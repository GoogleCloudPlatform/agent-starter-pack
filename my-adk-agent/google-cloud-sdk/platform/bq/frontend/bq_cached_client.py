#!/usr/bin/env python
"""BigQuery client that exists for some reason."""

import logging
import sys
import textwrap
from typing import Any, Dict, List, Optional, Type

from absl import app
from absl import flags
import httplib2
import termcolor

import bq_auth_flags
import bq_flags
import bq_utils
import credential_loader
from auth import main_credential_loader
from clients import bigquery_client
from clients import bigquery_client_extended
from clients import wait_printer
from frontend import utils as bq_frontend_utils
from utils import bq_api_utils
from utils import bq_gcloud_utils
from utils import bq_logging


FLAGS = flags.FLAGS




def _GetWaitPrinterFactoryFromFlags() -> Type[wait_printer.WaitPrinter]:
  """Returns the default wait_printer_factory to use while waiting for jobs."""
  if bq_flags.QUIET.value:
    return wait_printer.QuietWaitPrinter
  if bq_flags.HEADLESS.value:
    return wait_printer.TransitionWaitPrinter
  return wait_printer.VerboseWaitPrinter


class Client(object):
  """Class caching bigquery_client.BigqueryClient based on arguments."""

  client_cache = {}

  @staticmethod
  def _CollectArgs(config_logging: bool = True, **kwds) -> Dict[str, Any]:
    """Collect and combine FLAGS and kwds to create BQ Client.

    Args:
      config_logging: if True, set python logging according to --apilog.
      **kwds: keyword arguments for creating BigqueryClient.
    """

    def KwdsOrFlags(name: str):
      return kwds[name] if name in kwds else getattr(FLAGS, name)

    # Note that we need to handle possible initialization tasks
    # for the case of being loaded as a library.
    bq_utils.ProcessBigqueryrc()


    if config_logging:
      bq_logging.ConfigureLogging(bq_flags.APILOG.value)
    # Gcloud config currently gets processed twice.
    bq_gcloud_utils.process_config(flag_values=FLAGS)

    if (
        bq_flags.UNIVERSE_DOMAIN.present
        and not bq_api_utils.is_gdu_universe(bq_flags.UNIVERSE_DOMAIN.value)
        and not bq_auth_flags.USE_GOOGLE_AUTH.value
    ):
      logging.warning(
          'Attempting to use a non-GDU universe domain without setting'
          ' `use_google_auth`. You might need to set `use_google_auth` to True.'
      )

    if bq_flags.HTTPLIB2_DEBUGLEVEL.value:
      httplib2.debuglevel = bq_flags.HTTPLIB2_DEBUGLEVEL.value
      if hasattr(httplib2, 'python3'):
        httplib2.python3.debuglevel = bq_flags.HTTPLIB2_DEBUGLEVEL.value

    client_args = {}
    global_args = (
        'credential_file',
        'job_property',
        'project_id',
        'dataset_id',
        'trace',  # str
        'sync',
        'use_google_auth',
        'api',
        'api_version',
        'quota_project_id',
        'request_reason',
        'location',
    )
    for name in global_args:
      client_args[name] = KwdsOrFlags(name)

    logging.info(
        'Creating client for BQ CLI version: %s', bq_utils.VERSION_NUMBER
    )
    logging.debug('Global args collected: %s', client_args)

    client_args['wait_printer_factory'] = _GetWaitPrinterFactoryFromFlags()
    if bq_flags.DISCOVERY_FILE.value:
      with open(bq_flags.DISCOVERY_FILE.value) as f:
        client_args['discovery_document'] = f.read()
    client_args['enable_resumable_uploads'] = (
        True
        if bq_flags.ENABLE_RESUMABLE_UPLOADS.value is None
        else bq_flags.ENABLE_RESUMABLE_UPLOADS.value
    )
    if bq_flags.MAX_ROWS_PER_REQUEST.value:
      client_args['max_rows_per_request'] = bq_flags.MAX_ROWS_PER_REQUEST.value
    logging.info('Client args collected: %s', client_args)

    return client_args

  @staticmethod
  def GetCredentials(
      credentials: bigquery_client.LegacyAndGoogleAuthCredentialsUnionType,
      client_args: Dict[str, Any],
  ) -> bigquery_client.LegacyAndGoogleAuthCredentialsUnionType:
    """A function to lookup the credentials to use for this BQ CLI invocation.

    Args:
      credentials: bypass the credential lookup and use these instead.
      client_args: the client args collected from flags, kwds and bigqueryrc.

    Returns:
      The credentials ot use for this BQ CLI invocation.
    """
    if credentials is not None:
      logging.info('Credentials passed in directly')
    elif client_args.get('use_google_auth', False):
      logging.info('Credentials loaded using Google Auth')
      credentials = main_credential_loader.GetCredentialsFromFlags()
    else:
      logging.info('Credentials loaded using oauth2client')
      credentials = credential_loader.GetCredentialsFromFlags()
    assert credentials is not None
    return credentials

  @staticmethod
  def Create(
      config_logging: bool = True,
      credentials: bigquery_client.LegacyAndGoogleAuthCredentialsUnionType = None,
      **kwds,
  ) -> bigquery_client_extended.BigqueryClientExtended:
    """Build a new BigqueryClient configured from kwds and FLAGS.

    Args:
      config_logging: if True, set python logging according to --apilog.
      credentials: bypass the credential lookup and use these instead.
      **kwds: keyword arguments for creating BigqueryClient.

    Returns:
      A BigqueryClient from the kwds.
    """
    # Resolve flag values first.
    logging.debug('Collecting args before creating a BigqueryClient: %s', kwds)
    client_args = Client._CollectArgs(config_logging, **kwds)

    bigquery_client_factory = Factory.GetBigqueryClientFactory()
    return bigquery_client_factory(
        credentials=Client.GetCredentials(credentials, client_args),
        **client_args,
    )


  @classmethod
  def _GetClientCacheKey(cls, **kwds) -> str:
    logging.debug('In Client._GetClientCacheKey: %s', kwds)
    client_args = Client._CollectArgs(**kwds)
    return (
        'client_args={client_args},'
        'service_account_credential_file={service_account_credential_file},'
        'apilog={apilog},'.format(
            client_args=client_args,
            service_account_credential_file=bq_auth_flags.SERVICE_ACCOUNT_CREDENTIAL_FILE.value,
            apilog=bq_flags.APILOG.value,
        )
    )

  @classmethod
  def Get(cls) -> bigquery_client_extended.BigqueryClientExtended:
    """Return a BigqueryClient initialized from flags."""
    cache_key = Client._GetClientCacheKey()
    if cache_key in cls.client_cache:
      logging.info(
          'Using a cached client with previous auth and discovery docs from the'
          ' cache_key: %s',
          cache_key,
      )
    else:
      try:
        cls.client_cache[cache_key] = Client.Create()
        logging.info('Successfully created a new client.')
      except ValueError as e:
        logging.info('Failed to create a new client.')
        # Convert constructor parameter errors into flag usage errors.
        raise app.UsageError(e)

    return cls.client_cache[cache_key]


class Factory:
  """Class encapsulating factory creation of BigqueryClient."""

  _BIGQUERY_CLIENT_FACTORY = None

  class ClientTablePrinter:
    """Class encapsulating factory creation of TablePrinter."""

    _TABLE_PRINTER = None

    @classmethod
    def GetTablePrinter(cls) -> bq_frontend_utils.TablePrinter:
      if cls._TABLE_PRINTER is None:
        cls._TABLE_PRINTER = bq_frontend_utils.TablePrinter()
      return cls._TABLE_PRINTER

  @classmethod
  def GetBigqueryClientFactory(
      cls,
  ) -> Type[bigquery_client_extended.BigqueryClientExtended]:
    if cls._BIGQUERY_CLIENT_FACTORY is None:
      cls._BIGQUERY_CLIENT_FACTORY = (
          bigquery_client_extended.BigqueryClientExtended
      )
    return cls._BIGQUERY_CLIENT_FACTORY
