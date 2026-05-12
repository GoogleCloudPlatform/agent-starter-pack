#!/usr/bin/env python
"""Utilities to create Google Auth credentials."""

import logging
from typing import Union

from absl import app
from google.auth.compute_engine import credentials as compute_engine
from google.oauth2 import credentials as google_oauth2
from google.oauth2 import service_account

import bq_auth_flags
import bq_flags
import bq_utils
from auth import gcloud_credential_loader
from utils import bq_error


GoogleAuthCredentialsUnionType = Union[
    google_oauth2.Credentials,
    service_account.Credentials,
    compute_engine.Credentials,
]


def GetCredentialsFromFlags() -> GoogleAuthCredentialsUnionType:
  """Returns credentials based on BQ CLI auth flags.

  Returns: An OAuth2, compute engine, or service account credentials objects
  based on BQ CLI auth flag values.

  Raises:
  app.UsageError, invalid flag values.
  bq_error.BigqueryError, error getting credentials.
  """
  if bq_auth_flags.APPLICATION_DEFAULT_CREDENTIAL_FILE.value:
    raise app.UsageError(
        'The --application_default_credential_file flag is being deprecated.'
        ' For now, this flag can still be used by forcing the legacy'
        ' authentication library with --nouse_google_auth.'
    )
  if (
      bq_auth_flags.SERVICE_ACCOUNT_PRIVATE_KEY_PASSWORD.default
      != bq_auth_flags.SERVICE_ACCOUNT_PRIVATE_KEY_PASSWORD.value
  ):
    raise app.UsageError(bq_error.P12_DEPRECATION_MESSAGE)

  if bq_auth_flags.OAUTH_ACCESS_TOKEN.value:
    logging.info('Loading auth credentials from --oauth_access_token')
    return google_oauth2.Credentials(
        token=bq_auth_flags.OAUTH_ACCESS_TOKEN.value,
        quota_project_id=bq_utils.GetResolvedQuotaProjectID(
            bq_auth_flags.QUOTA_PROJECT_ID.value, bq_flags.PROJECT_ID.value
        ),
    )
  else:
    logging.info('No `oauth_access_token`, load credentials elsewhere')

  if bq_auth_flags.USE_GCE_SERVICE_ACCOUNT.value:
    logging.info('Loading auth credentials with --use_gce_service_account')
    return compute_engine.Credentials(
        quota_project_id=bq_utils.GetResolvedQuotaProjectID(
            bq_auth_flags.QUOTA_PROJECT_ID.value, bq_flags.PROJECT_ID.value
        ),
    )
  else:
    logging.info('No `use_gce_service_account`, load credentials elsewhere')

  if bq_auth_flags.SERVICE_ACCOUNT.value:
    raise app.UsageError(
        'The flag --service_account is not supported. '
        'To use a service account please follow'
        ' https://cloud.google.com/docs/authentication/'
        'use-service-account-impersonation#gcloud-config.'
    )


  return gcloud_credential_loader.LoadCredential()


