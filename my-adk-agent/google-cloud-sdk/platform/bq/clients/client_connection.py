#!/usr/bin/env python
"""The BigQuery CLI connection client library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
from typing import Any, Dict, List, Mapping, Optional

from googleapiclient import discovery
import inflection

from utils import bq_api_utils
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

Service = bq_api_utils.Service

# Data Transfer Service Authorization Info
AUTHORIZATION_CODE = 'authorization_code'
VERSION_INFO = 'version_info'

# Valid proto field name regex.
_VALID_FIELD_NAME_REGEXP = r'[0-9A-Za-z_]+'

# Connection field mask paths pointing to map keys.
_MAP_KEY_PATHS = [
    'configuration.parameters',
    'configuration.authentication.parameters',
]

_AUTH_PROFILE_ID_PATH = 'configuration.authentication.profile_id'
_AUTH_PATH = 'configuration.authentication'


def GetConnection(
    client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ConnectionReference,
):
  """Gets connection with the given connection reference.

  Arguments:
    client: the client used to make the request.
    reference: Connection to get.

  Returns:
    Connection object with the given id.
  """
  return (
      client.projects()
      .locations()
      .connections()
      .get(name=reference.path())
      .execute()
  )


def CreateConnection(
    client: discovery.Resource,
    project_id: str,
    location: str,
    connection_type: str,  # Actually a CONNECTION_TYPE_TO_PROPERTY_MAP key.
    properties: str,
    connection_credential: Optional[str] = None,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    connection_id: Optional[str] = None,
    kms_key_name: Optional[str] = None,
    connector_configuration: Optional[str] = None,
):
  """Create a connection with the given connection reference.

  Arguments:
    client: the client used to make the request.
    project_id: Project ID.
    location: Location of connection.
    connection_type: Type of connection, allowed values: ['CLOUD_SQL']
    properties: Connection properties in JSON format.
    connection_credential: Connection credentials in JSON format.
    display_name: Friendly name for the connection.
    description: Description of the connection.
    connection_id: Optional connection ID.
    kms_key_name: Optional KMS key name.
    connector_configuration: Optional configuration for connector.

  Returns:
    Connection object that was created.
  """

  connection = {}

  if display_name:
    connection['friendlyName'] = display_name

  if description:
    connection['description'] = description

  if kms_key_name:
    connection['kmsKeyName'] = kms_key_name

  property_name = bq_processor_utils.CONNECTION_TYPE_TO_PROPERTY_MAP.get(
      connection_type
  )
  if property_name:
    connection[property_name] = bq_processor_utils.ParseJson(properties)
    if connection_credential:
      if isinstance(connection[property_name], Mapping):
        connection[property_name]['credential'] = bq_processor_utils.ParseJson(
            connection_credential
        )
      else:
        raise ValueError('The `properties` were not a dictionary.')
  elif connector_configuration:
    connection['configuration'] = bq_processor_utils.ParseJson(
        connector_configuration
    )
  else:
    error = (
        'connection_type %s is unsupported or connector_configuration is not'
        ' specified' % connection_type
    )
    raise ValueError(error)

  parent = 'projects/%s/locations/%s' % (project_id, location)
  return (
      client.projects()
      .locations()
      .connections()
      .create(parent=parent, connectionId=connection_id, body=connection)
      .execute()
  )


def UpdateConnection(
    client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ConnectionReference,
    connection_type: Optional[
        str
    ] = None,  # Actually a CONNECTION_TYPE_TO_PROPERTY_MAP key.
    properties: Optional[str] = None,
    connection_credential: Optional[str] = None,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    kms_key_name: Optional[str] = None,
    connector_configuration: Optional[str] = None,
):
  """Update connection with the given connection reference.

  Arguments:
    client: the client used to make the request.
    reference: Connection to update
    connection_type: Type of connection, allowed values: ['CLOUD_SQL']
    properties: Connection properties
    connection_credential: Connection credentials in JSON format.
    display_name: Friendly name for the connection
    description: Description of the connection
    kms_key_name: Optional KMS key name.
    connector_configuration: Optional configuration for connector

  Raises:
    bq_error.BigqueryClientError: The connection type is not defined
      when updating
    connection_credential or properties.
  Returns:
    Connection object that was created.
  """

  if (connection_credential or properties) and not connection_type:
    raise bq_error.BigqueryClientError(
        'connection_type is required when updating connection_credential or'
        ' properties'
    )
  connection = {}
  update_mask = []

  if display_name:
    connection['friendlyName'] = display_name
    update_mask.append('friendlyName')

  if description:
    connection['description'] = description
    update_mask.append('description')

  if kms_key_name is not None:
    update_mask.append('kms_key_name')
  if kms_key_name:
    connection['kmsKeyName'] = kms_key_name

  if connection_type == 'CLOUD_SQL':
    if properties:
      cloudsql_properties = bq_processor_utils.ParseJson(properties)
      connection['cloudSql'] = cloudsql_properties

      update_mask.extend(
          _GetUpdateMask(connection_type.lower(), cloudsql_properties)
      )

    else:
      connection['cloudSql'] = {}

    if connection_credential:
      connection['cloudSql']['credential'] = bq_processor_utils.ParseJson(
          connection_credential
      )
      update_mask.append('cloudSql.credential')

  elif connection_type == 'AWS':

    if properties:
      aws_properties = bq_processor_utils.ParseJson(properties)
      connection['aws'] = aws_properties
      if aws_properties.get('crossAccountRole') and aws_properties[
          'crossAccountRole'
      ].get('iamRoleId'):
        update_mask.append('aws.crossAccountRole.iamRoleId')
      if aws_properties.get('accessRole') and aws_properties['accessRole'].get(
          'iamRoleId'
      ):
        update_mask.append('aws.access_role.iam_role_id')
    else:
      connection['aws'] = {}

    if connection_credential:
      connection['aws']['credential'] = bq_processor_utils.ParseJson(
          connection_credential
      )
      update_mask.append('aws.credential')

  elif connection_type == 'Azure':
    if properties:
      azure_properties = bq_processor_utils.ParseJson(properties)
      connection['azure'] = azure_properties
      if azure_properties.get('customerTenantId'):
        update_mask.append('azure.customer_tenant_id')
      if azure_properties.get('federatedApplicationClientId'):
        update_mask.append('azure.federated_application_client_id')

  elif connection_type == 'SQL_DATA_SOURCE':
    if properties:
      sql_data_source_properties = bq_processor_utils.ParseJson(properties)
      connection['sqlDataSource'] = sql_data_source_properties

      update_mask.extend(
          _GetUpdateMask(connection_type.lower(), sql_data_source_properties)
      )

    else:
      connection['sqlDataSource'] = {}

    if connection_credential:
      connection['sqlDataSource']['credential'] = bq_processor_utils.ParseJson(
          connection_credential
      )
      update_mask.append('sqlDataSource.credential')

  elif connection_type == 'CLOUD_SPANNER':
    if properties:
      cloudspanner_properties = bq_processor_utils.ParseJson(properties)
      connection['cloudSpanner'] = cloudspanner_properties
      update_mask.extend(
          _GetUpdateMask(connection_type.lower(), cloudspanner_properties)
      )
    else:
      connection['cloudSpanner'] = {}

  elif connection_type == 'SPARK':
    if properties:
      spark_properties = bq_processor_utils.ParseJson(properties)
      connection['spark'] = spark_properties
      if 'sparkHistoryServerConfig' in spark_properties:
        update_mask.append('spark.spark_history_server_config')
      if 'metastoreServiceConfig' in spark_properties:
        update_mask.append('spark.metastore_service_config')
    else:
      connection['spark'] = {}
  elif connector_configuration:
    connection['configuration'] = bq_processor_utils.ParseJson(
        connector_configuration
    )
    update_mask.extend(
        _GetUpdateMaskRecursively('configuration', connection['configuration'])
    )
    if _AUTH_PROFILE_ID_PATH in update_mask and _AUTH_PATH not in update_mask:
      update_mask.append(_AUTH_PATH)

  return (
      client.projects()
      .locations()
      .connections()
      .patch(
          name=reference.path(),
          updateMask=','.join(update_mask),
          body=connection,
      )
      .execute()
  )


def _GetUpdateMask(
    base_path: str, json_properties: Dict[str, Any]
) -> List[str]:
  """Creates an update mask from json_properties.

  Arguments:
    base_path: 'cloud_sql'
    json_properties: { 'host': ... , 'instanceId': ... }

  Returns:
      list of  paths in snake case:
      mask = ['cloud_sql.host', 'cloud_sql.instance_id']
  """
  return [
      base_path + '.' + inflection.underscore(json_property)
      for json_property in json_properties
  ]


def _EscapeIfRequired(prefix: str, name: str) -> str:
  """Escapes name if it points to a map key or converts it to snake case.

  If name points to a map key:
  1. Do not change the name.
  2. Escape name with backticks if it is not a valid proto field name.

  Args:
    prefix: field mask prefix to check if name points to a map key.
    name: name of the field.

  Returns:
    escaped name
  """
  if prefix in _MAP_KEY_PATHS:
    return (
        name
        if re.fullmatch(_VALID_FIELD_NAME_REGEXP, name)
        else ('`' + name + '`')
    )

  # Otherwise, convert name to snake case
  return inflection.underscore(name)


def _GetUpdateMaskRecursively(
    prefix: str, json_value: Dict[str, Any]
) -> List[str]:
  """Recursively traverses json_value and returns a list of update mask paths.

  Args:
    prefix: current prefix of the json value.
    json_value: value to traverse.

  Returns:
    a field mask containing all the set paths in the json value.
  """
  if not isinstance(json_value, dict) or not json_value:
    return [prefix]

  result = []
  for name in json_value:
    new_prefix = prefix + '.' + _EscapeIfRequired(prefix, name)
    new_json_value = json_value.get(name)
    result.extend(_GetUpdateMaskRecursively(new_prefix, new_json_value))

  return result


def DeleteConnection(
    client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ConnectionReference,
):
  """Delete a connection with the given connection reference.

  Arguments:
    client: the client used to make the request.
    reference: Connection to delete.
  """
  client.projects().locations().connections().delete(
      name=reference.path()
  ).execute()


def ListConnections(
    client: discovery.Resource,
    project_id: str,
    location: str,
    max_results: int,
    page_token: Optional[str],
):
  """List connections in the project and location for the given reference.

  Arguments:
    client: the client used to make the request.
    project_id: Project ID.
    location: Location.
    max_results: Number of results to show.
    page_token: Token to retrieve the next page of results.

  Returns:
    List of connection objects
  """
  parent = 'projects/%s/locations/%s' % (project_id, location)
  return (
      client.projects()
      .locations()
      .connections()
      .list(parent=parent, pageToken=page_token, pageSize=max_results)
      .execute()
  )


def SetConnectionIAMPolicy(
    client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ConnectionReference,
    policy: str,
):
  """Sets IAM policy for the given connection resource.

  Arguments:
    client: the client used to make the request.
    reference: the ConnectionReference for the connection resource.
    policy: The policy string in JSON format.

  Returns:
    The updated IAM policy attached to the given connection resource.

  Raises:
    BigqueryTypeError: if reference is not a ConnectionReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ConnectionReference,
      method='SetConnectionIAMPolicy',
  )
  return (
      client.projects()
      .locations()
      .connections()
      .setIamPolicy(resource=reference.path(), body={'policy': policy})
      .execute()
  )


def GetConnectionIAMPolicy(
    client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ConnectionReference,
):
  """Gets IAM policy for the given connection resource.

  Arguments:
    client: the client used to make the request.
    reference: the ConnectionReference for the connection resource.

  Returns:
    The IAM policy attached to the given connection resource.

  Raises:
    BigqueryTypeError: if reference is not a ConnectionReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ConnectionReference,
      method='GetConnectionIAMPolicy',
  )
  return (
      client.projects()
      .locations()
      .connections()
      .getIamPolicy(resource=reference.path())
      .execute()
  )
