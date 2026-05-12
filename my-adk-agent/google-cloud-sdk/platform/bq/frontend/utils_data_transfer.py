#!/usr/bin/env python
"""The BigQuery CLI update command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import flags

from clients import client_data_transfer
from frontend import utils as frontend_utils

FLAGS = flags.FLAGS


def CheckValidCreds(reference, data_source, transfer_client):
  """Checks valid credentials.

  Checks if Data Transfer Service valid credentials exist for the given data
  source and requesting user. Some data sources don't support service account,
  so we need to talk to them on behalf of the end user. This method just checks
  whether we have OAuth token for the particular user, which is a pre-requisite
  before a user can create a transfer config.

  Args:
    reference: The project reference.
    data_source: The data source of the transfer config.
    transfer_client: The transfer api client.

  Returns:
    credentials: It contains an instance of CheckValidCredsResponse if valid
    credentials exist.
  """
  credentials = None
  if FLAGS.location:
    data_source_reference = (
        reference
        + '/locations/'
        + FLAGS.location
        + '/dataSources/'
        + data_source
    )
    credentials = (
        transfer_client.projects()
        .locations()
        .dataSources()
        .checkValidCreds(name=data_source_reference, body={})
        .execute()
    )
  else:
    data_source_reference = reference + '/dataSources/' + data_source
    credentials = (
        transfer_client.projects()
        .dataSources()
        .checkValidCreds(name=data_source_reference, body={})
        .execute()
    )
  return credentials


def RetrieveAuthorizationInfo(reference, data_source, transfer_client):
  """Retrieves the authorization code.

  An authorization code is needed if the Data Transfer Service does not
  have credentials for the requesting user and data source. The Data
  Transfer Service will convert this authorization code into a refresh
  token to perform transfer runs on the user's behalf.

  Args:
    reference: The project reference.
    data_source: The data source of the transfer config.
    transfer_client: The transfer api client.

  Returns:
    auth_info: A dict which contains authorization info from user. It is either
    an authorization_code or a version_info.
  """
  data_source_retrieval = reference + '/dataSources/' + data_source
  data_source_info = (
      transfer_client.projects()
      .dataSources()
      .get(name=data_source_retrieval)
      .execute()
  )
  auth_uri = (
      'https://bigquery.cloud.google.com/datatransfer/oauthz/auth?client_id='
      + data_source_info['clientId']
      + '&scope='
      + '%20'.join(data_source_info['scopes'])
      + '&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=consent_user'
  )
  print('\n' + auth_uri)

  auth_info = {}
  print(
      'Please copy and paste the above URL into your web browser'
      ' and follow the instructions to retrieve a version_info.'
  )
  auth_info[client_data_transfer.VERSION_INFO] = frontend_utils.RawInput(
      'Enter your version_info here: '
  )

  return auth_info
