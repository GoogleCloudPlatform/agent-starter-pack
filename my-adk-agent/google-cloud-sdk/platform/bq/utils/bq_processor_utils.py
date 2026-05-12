#!/usr/bin/env python
# pylint: disable=g-unknown-interpreter
# Copyright 2012 Google Inc. All Rights Reserved.
"""Bigquery Client library for Python."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import os
import re
from typing import Any, Dict, List, NamedTuple, Optional, TypedDict

from utils import bq_error
from utils import bq_id_utils

# Maximum number of jobs that can be retrieved by ListJobs (sanity limit).
MAX_RESULTS = 100000

GCS_SCHEME_PREFIX = 'gs://'


# Maps supported connection type names to the corresponding property in the
# connection proto.
CONNECTION_TYPE_TO_PROPERTY_MAP = {
    'CLOUD_SQL': 'cloudSql',
    'AWS': 'aws',
    'Azure': 'azure',
    'SQL_DATA_SOURCE': 'sqlDataSource',
    'CLOUD_SPANNER': 'cloudSpanner',
    'CLOUD_RESOURCE': 'cloudResource',
    'SPARK': 'spark',
}
CONNECTION_PROPERTY_TO_TYPE_MAP = {
    p: t for t, p in CONNECTION_TYPE_TO_PROPERTY_MAP.items()
}
CONNECTION_TYPES = CONNECTION_TYPE_TO_PROPERTY_MAP.keys()


def MakeAccessRolePropertiesJson(iam_role_id: str) -> str:
  """Returns properties for a connection with IAM role id.

  Args:
    iam_role_id: IAM role id.

  Returns:
    JSON string with properties to create a connection with IAM role id.
  """

  return '{"accessRole": {"iamRoleId": "%s"}}' % iam_role_id


def MakeTenantIdPropertiesJson(tenant_id: str) -> str:
  """Returns properties for a connection with tenant id.

  Args:
    tenant_id: tenant id.

  Returns:
    JSON string with properties to create a connection with customer's tenant
    id.
  """

  return '{"customerTenantId": "%s"}' % tenant_id


def MakeAzureFederatedAppClientIdPropertiesJson(
    federated_app_client_id: str,
) -> str:
  """Returns properties for a connection with a federated app (client) id.

  Args:
    federated_app_client_id: federated application (client) id.

  Returns:
    JSON string with properties to create a connection with customer's federated
    application (client) id.
  """

  return '{"federatedApplicationClientId": "%s"}' % federated_app_client_id


def MakeAzureFederatedAppClientAndTenantIdPropertiesJson(
    tenant_id: str, federated_app_client_id: str
) -> str:
  """Returns properties for a connection with tenant and federated app ids.

  Args:
    tenant_id: tenant id
    federated_app_client_id: federated application (client) id.

  Returns:
    JSON string with properties to create a connection with customer's tenant
    and federated application (client) ids.
  """

  return '{"customerTenantId": "%s", "federatedApplicationClientId" : "%s"}' % (
      tenant_id,
      federated_app_client_id,
  )




def ToLowerCamel(name: str) -> str:
  """Convert a name with underscores to camelcase."""
  return re.sub('_[a-z]', lambda match: match.group(0)[1].upper(), name)


def ApplyParameters(config, **kwds) -> None:
  """Adds all kwds to config dict, adjusting keys to camelcase.

  Note this does not remove entries that are set to None, however.

  Args:
    config: A configuration dict.
    **kwds: A dict of keys and values to set in the config.
  """
  config.update((ToLowerCamel(k), v) for k, v in kwds.items() if v is not None)


def FormatProjectIdentifierForTransfers(
    project_reference: 'bq_id_utils.ApiClientHelper.ProjectReference',
    location: str,
) -> str:
  """Formats a project identifier for data transfers.

  Data transfer API calls take in the format projects/(projectName), so because
  by default project IDs take the format (projectName), add the beginning format
  to perform data transfer commands

  Args:
    project_reference: The project id to format for data transfer commands.
    location: The location id, e.g. 'us' or 'eu'.

  Returns:
    The formatted project name for transfers.
  """

  return 'projects/' + project_reference.projectId + '/locations/' + location


def ParseJson(
    json_string: Optional[str],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
  """Wrapper for standard json parsing, may throw BigQueryClientError."""
  try:
    return json.loads(json_string)
  except ValueError as e:
    raise bq_error.BigqueryClientError(
        'Error decoding JSON from string %s: %s' % (json_string, e)
    )


class InsertEntry(NamedTuple):
  insert_id: Optional[str]  # Optional here is to support legacy tests.
  record: object


def JsonToInsertEntry(
    insert_id: Optional[str],  # Optional here is to support legacy tests.
    json_string: str,
) -> InsertEntry:
  """Parses a JSON encoded record and returns an InsertEntry.

  Arguments:
    insert_id: Id for the insert, can be None.
    json_string: The JSON encoded data to be converted.

  Returns:
    InsertEntry object for adding to a table.
  """
  try:
    row = json.loads(json_string)
    if not isinstance(row, dict):
      raise bq_error.BigqueryClientError('Value is not a JSON object')
    return InsertEntry(insert_id, row)
  except ValueError as e:
    raise bq_error.BigqueryClientError('Could not parse object: %s' % (str(e),))


def GetSessionId(job):
  """Helper to return the session id if the job is part of one.

  Args:
    job: a job resource to get statistics and sessionInfo from.

  Returns:
    sessionId, if the job is part of a session.
  """
  stats = job.get('statistics', {})
  if 'sessionInfo' in stats and 'sessionId' in stats['sessionInfo']:
    return stats['sessionInfo']['sessionId']
  return None


def GetJobTypeName(job_info):
  """Helper for job printing code."""
  job_names = set(('extract', 'load', 'query', 'copy'))
  try:
    return (
        set(job_info.get('configuration', {}).keys())
        .intersection(job_names)
        .pop()
    )
  except KeyError:
    return None


def ProcessSources(source_string: str) -> List[str]:
  """Take a source string and return a list of URIs.

  The list will consist of either a single local filename, which
  we check exists and is a file, or a list of gs:// uris.

  Args:
    source_string: A comma-separated list of URIs.

  Returns:
    List of one or more valid URIs, as strings.

  Raises:
    bq_error.BigqueryClientError: if no valid list of sources can be
      determined.
  """
  sources = [source.strip() for source in source_string.split(',')]
  gs_uris = [
      source for source in sources if source.startswith(GCS_SCHEME_PREFIX)
  ]
  if not sources:
    raise bq_error.BigqueryClientError('No sources specified')
  if gs_uris:
    if len(gs_uris) != len(sources):
      raise bq_error.BigqueryClientError(
          'All URIs must begin with "{}" if any do.'.format(GCS_SCHEME_PREFIX)
      )
    return sources
  else:
    source = sources[0]
    if len(sources) > 1:
      raise bq_error.BigqueryClientError(
          'Local upload currently supports only one file, found %d'
          % (len(sources),)
      )
    if not os.path.exists(source):
      raise bq_error.BigqueryClientError(
          'Source file not found: %s' % (source,)
      )
    if not os.path.isfile(source):
      raise bq_error.BigqueryClientError(
          'Source path is not a file: %s' % (source,)
      )
  return sources


def KindToName(kind):
  """Convert a kind to just a type name."""
  return kind.partition('#')[2]


def GetConnectionType(connection):
  for t, p in CONNECTION_TYPE_TO_PROPERTY_MAP.items():
    if p in connection:
      return t
  return None


def ConstructObjectReference(object_info):
  """Construct a Reference from a server response."""
  if 'kind' in object_info:
    typename = KindToName(object_info['kind'])
    lower_camel = typename + 'Reference'
    if lower_camel not in object_info:
      raise ValueError(
          'Cannot find %s in object of type %s: %s'
          % (lower_camel, typename, object_info)
      )
  else:
    typename = ''
    keys = [k for k in object_info if k.endswith('Reference')]
    if len(keys) != 1:
      raise ValueError(
          'Expected one Reference, found %s: %s' % (len(keys), keys)
      )
    lower_camel = keys[0]
  upper_camel = lower_camel[0].upper() + lower_camel[1:]
  reference_type = getattr(bq_id_utils.ApiClientHelper, upper_camel, None)
  if reference_type is None:
    raise ValueError('Unknown reference type: %s' % (typename,))
  return reference_type.Create(**object_info[lower_camel])


def ConstructObjectInfo(reference):
  """Construct an Object from an ObjectReference."""
  typename = reference.__class__.__name__
  lower_camel = typename[0].lower() + typename[1:]
  return {lower_camel: dict(reference)}


def PrepareListRequest(
    reference,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    filter_expression: Optional[str] = None,
):
  """Create and populate a list request."""
  request = dict(reference)
  if max_results is not None:
    request['maxResults'] = max_results
  if filter_expression is not None:
    request['filter'] = filter_expression
  if page_token is not None:
    request['pageToken'] = page_token
  return request


## Data transfer request types

# pylint: disable=invalid-name


class TransferListRequest(TypedDict):
  parent: str
  pageSize: Optional[int]
  pageToken: Optional[str]
  dataSourceIds: Optional[List[str]]


# pylint: enable=invalid-name


def PrepareTransferListRequest(
    reference: bq_id_utils.ApiClientHelper.ProjectReference,
    location: str,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    data_source_ids: Optional[str] = None,
) -> TransferListRequest:
  """Create and populate a list request."""
  request = dict(
      parent=FormatProjectIdentifierForTransfers(reference, location)
  )
  if page_size is not None:
    request['pageSize'] = page_size
  if page_token is not None:
    request['pageToken'] = page_token
  if data_source_ids is not None:
    data_source_ids = data_source_ids.split(':')
    if data_source_ids[0] == 'dataSourceIds':
      data_source_ids = data_source_ids[1].split(',')
      request['dataSourceIds'] = data_source_ids
    else:
      raise bq_error.BigqueryError(
          "Invalid filter flag values: '%s'. "
          "Expected format: '--filter=dataSourceIds:id1,id2'"
          % data_source_ids[0]
      )

  return request


def ParseStateFilterExpression(
    filter_expression: Optional[str] = None,
) -> Optional[List[str]]:
  """Parses the state filter for list jobs.

  Args:
    filter_expression: A string containing the state filter, e.g., 'state:done'.

  Returns:
    A single state filter or a list of filters to apply. Returns None if no
    filter is provided.

  Raises:
    bq_error.BigqueryClientError: if the filter expression is invalid.
  """
  if filter_expression is None:
    return None
  if filter_expression.startswith('states:'):
    try:
      return filter_expression.split(':')[1].split(',')
    except IndexError as e:
      raise bq_error.BigqueryError(
          'Invalid flag argument "' + filter_expression + '"'
      ) from e
  else:
    raise bq_error.BigqueryError(
        'Invalid flag argument "'
        + filter_expression
        + ', the expression must start with "states:"'
    )


def PrepareTransferRunListRequest(
    reference: str,
    run_attempt: Optional[str],
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    states: Optional[str] = None,
):
  """Create and populate a transfer run list request."""
  request = dict(parent=reference)
  request['runAttempt'] = run_attempt
  if max_results is not None:
    if max_results > MAX_RESULTS:
      max_results = MAX_RESULTS
    request['pageSize'] = max_results
  if states is not None:
    request['states'] = ParseStateFilterExpression(states)
  if page_token is not None:
    request['pageToken'] = page_token
  return request


def PrepareListTransferLogRequest(
    reference: str,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    message_type: Optional[str] = None,
):
  """Create and populate a transfer log list request."""
  request = dict(parent=reference)
  if max_results is not None:
    if max_results > MAX_RESULTS:
      max_results = MAX_RESULTS
    request['pageSize'] = max_results
  if page_token is not None:
    request['pageToken'] = page_token
  if message_type is not None:
    if 'messageTypes:' in message_type:
      try:
        message_type = message_type.split(':')[1].split(',')
        request['messageTypes'] = message_type
      except IndexError as e:
        raise bq_error.BigqueryError(
            'Invalid flag argument "' + message_type + '"'
        ) from e
    else:
      raise bq_error.BigqueryError(
          'Invalid flag argument "' + message_type + '"'
      )
  return request


def ProcessParamsFlag(params: str, items: Dict[str, Any]):
  """Processes the params flag.

  Args:
    params: The user specified parameters. The parameters should be in JSON
      format given as a string. Ex: --params="{'param':'value'}".
    items: The body that contains information of all the flags set.

  Returns:
    items: The body after it has been updated with the params flag.

  Raises:
    bq_error.BigqueryError: If there is an error with the given params.
  """
  try:
    parsed_params = json.loads(params)
  except Exception as e:
    raise bq_error.BigqueryError(
        'Parameters should be specified in JSON format when creating the'
        ' transfer configuration.'
    ) from e
  items['params'] = parsed_params
  return items


def ProcessRefreshWindowDaysFlag(
    refresh_window_days: str,
    data_source_info: Dict[str, Any],
    items: Dict[str, Any],
    data_source: str,
):
  """Processes the Refresh Window Days flag.

  Args:
    refresh_window_days: The user specified refresh window days.
    data_source_info: The data source of the transfer config.
    items: The body that contains information of all the flags set.
    data_source: The data source of the transfer config.

  Returns:
    items: The body after it has been updated with the
    refresh window days flag.
  Raises:
    bq_error.BigqueryError: If the data source does not support (custom)
      window days.
  """
  if 'dataRefreshType' in data_source_info:
    if data_source_info['dataRefreshType'] == 'CUSTOM_SLIDING_WINDOW':
      items['data_refresh_window_days'] = refresh_window_days
      return items
    else:
      raise bq_error.BigqueryError(
          "Data source '%s' does not support custom refresh window days."
          % data_source
      )
  else:
    raise bq_error.BigqueryError(
        "Data source '%s' does not support refresh window days." % data_source
    )
