#!/usr/bin/env python
"""BQ CLI helper functions for authentication."""

import os

import bq_flags
import bq_utils


_DEFAULT_TOKEN_HOST = 'https://oauth2.googleapis.com/token'
_DEFAULT_MTLS_TOKEN_HOST = 'https://oauth2.mtls.googleapis.com/token'


_CLOUD_CLI_CLIENT_ID = '32555940559.apps.googleusercontent.com'
_CLOUD_CLI_CLIENT_SECRET = 'ZmssLNjJy2998hD4CTg2ejr2'
_CLOUD_CLI_CLIENT_USER_AGENT = 'google-cloud-sdk' + os.environ.get(
    'CLOUDSDK_VERSION', bq_utils.VERSION_NUMBER
)

_BQ_CLI_CLIENT_ID = '977385342095.apps.googleusercontent.com'
_BQ_CLI_CLIENT_SECRET = 'wbER7576mc_1YOII0dGk7jEE'
_BQ_CLI_CLIENT_USER_AGENT = 'bq/' + bq_utils.VERSION_NUMBER


def get_client_id() -> str:
  if os.environ.get('CLOUDSDK_WRAPPER') == '1':
    return _CLOUD_CLI_CLIENT_ID
  else:
    return _BQ_CLI_CLIENT_ID


def get_client_secret() -> str:
  if os.environ.get('CLOUDSDK_WRAPPER') == '1':
    return _CLOUD_CLI_CLIENT_SECRET
  else:
    return _BQ_CLI_CLIENT_SECRET


def get_client_user_agent() -> str:
  if os.environ.get('CLOUDSDK_WRAPPER') == '1':
    return _CLOUD_CLI_CLIENT_USER_AGENT
  else:
    return _BQ_CLI_CLIENT_USER_AGENT


def get_token_uri() -> str:
  # TODO: b/394417874 - Read user's gcloud properties too.
  if bq_flags.MTLS.value:
    return _DEFAULT_MTLS_TOKEN_HOST
  return _DEFAULT_TOKEN_HOST
