#!/usr/bin/env python
"""BQ CLI helper functions for error handling."""

import codecs
import http.client
import logging
import sys
import textwrap
import time
import traceback
from typing import Optional

from absl import app
from absl import flags
from google.auth import exceptions as google_auth_exceptions
import googleapiclient
import httplib2
import oauth2client_4_0.client

import bq_utils
from gcloud_wrapper import bq_to_gcloud_config_classes
from utils import bq_error
from utils import bq_gcloud_utils
from utils import bq_logging
from pyglib import stringutil


FLAGS = flags.FLAGS

_BIGQUERY_TOS_MESSAGE = (
    'In order to get started, please visit the Google APIs Console to '
    'create a project and agree to our Terms of Service:\n'
    '\thttps://console.cloud.google.com/\n\n'
    'For detailed sign-up instructions, please see our Getting Started '
    'Guide:\n'
    '\thttps://cloud.google.com/bigquery/docs/quickstarts/'
    'quickstart-command-line\n\n'
    'Once you have completed the sign-up process, please try your command '
    'again.'
)


def text_wrap_error_message(
    text: str,
    length: Optional[int] = None,
    indent: str = '',
    drop_whitespace: bool = False,
) -> str:
  """Wraps a given text to a maximum line length and returns it.

  It turns lines that only contain whitespace into empty lines, keeps new lines,
  and expands tabs using 4 spaces.

  Args:
    text: str, text to wrap.
    length: int, maximum length of a line, includes indentation. If this is None
      then use get_help_width()
    indent: str, indent for all but first line.
    drop_whitespace: bool, whether to drop whitespace from the text after
      wrapping.

  Returns:
    str, the wrapped text.

  Raises:
    ValueError: Raised if indent or firstline_indent not shorter than length.
  """
  # Get defaults where callee used None
  if length is None:
    length = flags.get_help_width()
  if indent is None:
    indent = ''

  if len(indent) >= length:
    raise ValueError('Length of indent exceeds length')

  text = text.expandtabs(4)

  result = []
  wrapper = textwrap.TextWrapper(
      width=length,
      initial_indent=indent,
      subsequent_indent=indent,
      drop_whitespace=drop_whitespace,
  )

  # textwrap does not have any special treatment for newlines. From the docs:
  # "...newlines may appear in the middle of a line and cause strange output.
  # For this reason, text should be split into paragraphs (using
  # str.splitlines() or similar) which are wrapped separately."
  for paragraph in (p.rstrip() for p in text.splitlines()):
    if paragraph:
      result.extend([line.rstrip() for line in wrapper.wrap(paragraph)])
    else:
      result.append('')  # Keep empty lines.
    # Replace initial wrapper with wrapper for subsequent paragraphs.

  return '\n'.join(result)


def process_error(
    err: BaseException,
    name: str = 'unknown',
    message_prefix: str = 'You have encountered a bug in the BigQuery CLI.',
) -> int:
  """Translate an error message into some printing and a return code."""

  bq_logging.ConfigurePythonLogger(FLAGS.apilog)
  logger = logging.getLogger(__name__)

  if isinstance(err, SystemExit):
    logger.exception('An error has caused the tool to exit', exc_info=err)
    return err.code  # sys.exit called somewhere, hopefully intentionally.

  response = []
  retcode = 1

  etype, value, tb = sys.exc_info()
  trace = ''.join(traceback.format_exception(etype, value, tb))
  contact_us_msg = _generate_contact_us_message()
  platform_str = bq_utils.GetPlatformString()
  error_details = (
      textwrap.dedent("""\
     ========================================
     == Platform ==
       %s
     == bq version ==
       %s
     == Command line ==
       %s
     == UTC timestamp ==
       %s
     == Error trace ==
     %s
     ========================================
     """)
      % (
          platform_str,
          stringutil.ensure_str(bq_utils.VERSION_NUMBER),
          [stringutil.ensure_str(item) for item in sys.argv],
          time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
          stringutil.ensure_str(trace),
      )
  )

  codecs.register_error('strict', codecs.replace_errors)
  message = bq_logging.EncodeForPrinting(err)
  if isinstance(
      err, (bq_error.BigqueryNotFoundError, bq_error.BigqueryDuplicateError)
  ):
    response.append('BigQuery error in %s operation: %s' % (name, message))
    retcode = 2
  elif isinstance(err, bq_error.BigqueryTermsOfServiceError):
    response.append(str(err) + '\n')
    response.append(_BIGQUERY_TOS_MESSAGE)
  elif isinstance(err, bq_error.BigqueryInvalidQueryError):
    response.append('Error in query string: %s' % (message,))
  elif (
      isinstance(err, bq_error.BigqueryServiceError)
      and 'API requires a quota project, which is not set by default' in message
  ):
    response.append(
        'Bigquery service returned an error in %s operation: %s.'
        '\n\n'
        'Please make sure you have the correct quota project ID set through '
        '--quota_project_id or gcloud config set billing/quota_project. '
        % (name, message)
    )
  elif isinstance(err, bq_error.BigqueryError) and not isinstance(
      err, bq_error.BigqueryInterfaceError
  ):
    response.append('BigQuery error in %s operation: %s' % (name, message))
  elif isinstance(err, (app.UsageError, bq_error.BigqueryTypeError)):
    response.append(message)
  elif isinstance(
      err, (bq_to_gcloud_config_classes.BigqueryGcloudDelegationUserError)
  ):
    response.append(message)
  elif isinstance(err, SyntaxError) or isinstance(
      err, bq_error.BigquerySchemaError
  ):
    response.append('Invalid input: %s' % (message,))
  elif isinstance(err, flags.Error):
    response.append('Error parsing command: %s' % (message,))
  elif isinstance(err, KeyboardInterrupt):
    response.append('')
  else:  # pylint: disable=broad-except
    # Errors with traceback information are printed here.
    # The traceback module has nicely formatted the error trace
    # for us, so we don't want to undo that via TextWrap.
    if isinstance(err, bq_error.BigqueryInterfaceError):
      message_prefix = (
          'Bigquery service returned an invalid reply in %s operation: %s.'
          '\n\n'
          'Please make sure you are using the latest version '
          'of the bq tool and try again. '
          'If this problem persists, you may have encountered a bug in the '
          'bigquery client.' % (name, message)
      )
    elif isinstance(err, oauth2client_4_0.client.Error):
      message_prefix = (
          'Authorization error. This may be a network connection problem, '
          'so please try again. If this problem persists, the credentials '
          'may be corrupt. Try deleting and re-creating your credentials. '
          'You can delete your credentials using '
          '"bq init --delete_credentials".'
          '\n\n'
          'If this problem still occurs, you may have encountered a bug '
          'in the bigquery client.'
      )
    elif isinstance(err, google_auth_exceptions.RefreshError):
      credential_type = 'service account'
      message_prefix = (
          'Authorization error. If you used %s credentials, the server likely '
          'returned an Unauthorized response. Verify that you are using the '
          'correct account with the correct permissions to access the service '
          'endpoint.'
          '\n\n'
          'If this problem still occurs, you may have encountered a bug '
          'in the bigquery client.' % (credential_type)
      )
    elif (
        isinstance(err, http.client.HTTPException)
        or isinstance(err, googleapiclient.errors.Error)
        or isinstance(err, httplib2.HttpLib2Error)
    ):
      message_prefix = (
          'Network connection problem encountered, please try again.'
          '\n\n'
          'If this problem persists, you may have encountered a bug in the '
          'bigquery client.'
      )

    message = message_prefix + ' ' + contact_us_msg
    wrap_error_message = True
    if wrap_error_message:
      message = flags.text_wrap(message)
    print(message)
    print(error_details)
    response.append(
        'Unexpected exception in %s operation: %s' % (name, message)
    )

  response_message = '\n'.join(response)
  wrap_error_message = True
  if wrap_error_message:
    # Use our own text wrap function to preserve the traceback format.
    if 'Traceback' in response_message:
      response_message = text_wrap_error_message(response_message)
    else:
      response_message = flags.text_wrap(response_message)
  logger.exception(response_message, exc_info=err)
  print(response_message)
  return retcode


def _generate_contact_us_message() -> str:
  """Generates the Contact Us message."""
  # pragma pylint: disable=line-too-long
  contact_us_msg = (
      'Please file a bug report in our '
      'public '
      'issue tracker:\n'
      '  https://issuetracker.google.com/issues/new?component=187149&template=0\n'
      'Please include a brief description of '
      'the steps that led to this issue, as well as '
      'any rows that can be made public from '
      'the following information: \n\n'
  )

  # If an internal user runs the public BQ CLI, show the internal issue tracker.
  try:
    gcloud_configs = bq_gcloud_utils.load_config()
    gcloud_core_properties = gcloud_configs.get('core')
    if (
        'account' in gcloud_core_properties
        and '@google.com' in gcloud_core_properties['account']
    ):
      contact_us_msg = contact_us_msg.replace('public', 'internal').replace(
          'https://issuetracker.google.com/issues/new?component=187149&template=0',
          'http://b/issues/new?component=60322&template=178900',
      )
  except Exception:  # pylint: disable=broad-exception-caught
    # No-op if unable to determine the active account using gcloud.
    pass

  return contact_us_msg
