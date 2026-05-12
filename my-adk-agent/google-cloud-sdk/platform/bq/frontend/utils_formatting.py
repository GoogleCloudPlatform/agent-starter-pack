#!/usr/bin/env python
"""BQ CLI frontend formatting library for Python."""

import collections
import datetime
import json
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast

from typing_extensions import TypeAlias

import table_formatter
from clients import utils as bq_client_utils
from utils import bq_api_utils
from utils import bq_consts
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

collections_abc = collections
if sys.version_info > (3, 8):
  collections_abc = collections.abc

Service = bq_api_utils.Service

_COLUMNS_TO_INCLUDE_FOR_TRANSFER_RUN = [
    'updateTime',
    'schedule',
    'runTime',
    'scheduleTime',
    'params',
    'endTime',
    'dataSourceId',
    'destinationDatasetId',
    'state',
    'startTime',
    'name',
]


# These columns appear to be empty with scheduling a new transfer run
# so there are listed as excluded from the transfer run output.
_COLUMNS_EXCLUDED_FOR_MAKE_TRANSFER_RUN = ['schedule', 'endTime', 'startTime']


def _print_formatted_json_object(
    obj, obj_format: bq_consts.FormatType = 'json'
):
  """Prints obj in a JSON format according to the format argument.

  Args:
    obj: The object to print.
    obj_format: The format to use: 'json' or 'prettyjson'.
  """
  json_formats = ['json', 'prettyjson']

  if obj_format == 'json':
    print(json.dumps(obj, separators=(',', ':')))
  elif obj_format == 'prettyjson':
    print(json.dumps(obj, sort_keys=True, indent=2))
  else:
    raise ValueError(
        "Invalid json format for printing: '%s', expected one of: %s"
        % (obj_format, json_formats)
    )


def maybe_print_manual_instructions_for_connection(
    connection, flag_format: Optional[bq_consts.FormatType] = None
) -> None:
  """Prints follow-up instructions for created or updated connections."""

  if not connection:
    return

  if connection.get('aws') and connection['aws'].get('crossAccountRole'):
    obj = {
        'iamRoleId': connection['aws']['crossAccountRole'].get('iamRoleId'),
        'iamUserId': connection['aws']['crossAccountRole'].get('iamUserId'),
        'externalId': connection['aws']['crossAccountRole'].get('externalId'),
    }
    if flag_format in ['prettyjson', 'json']:
      _print_formatted_json_object(obj, obj_format=flag_format)
    else:
      print(
          (
              "Please add the following identity to your AWS IAM Role '%s'\n"
              "IAM user: '%s'\n"
              "External Id: '%s'\n"
          )
          % (
              connection['aws']['crossAccountRole'].get('iamRoleId'),
              connection['aws']['crossAccountRole'].get('iamUserId'),
              connection['aws']['crossAccountRole'].get('externalId'),
          )
      )

  if connection.get('aws') and connection['aws'].get('accessRole'):
    obj = {
        'iamRoleId': connection['aws']['accessRole'].get('iamRoleId'),
        'identity': connection['aws']['accessRole'].get('identity'),
    }
    if flag_format in ['prettyjson', 'json']:
      _print_formatted_json_object(obj, obj_format=flag_format)
    else:
      print(
          (
              "Please add the following identity to your AWS IAM Role '%s'\n"
              "Identity: '%s'\n"
          )
          % (
              connection['aws']['accessRole'].get('iamRoleId'),
              connection['aws']['accessRole'].get('identity'),
          )
      )

  if connection.get('azure') and connection['azure'].get(
      'federatedApplicationClientId'
  ):
    obj = {
        'federatedApplicationClientId': (
            connection['azure'].get('federatedApplicationClientId')
        ),
        'identity': connection['azure'].get('identity'),
    }
    if flag_format in ['prettyjson', 'json']:
      _print_formatted_json_object(obj, obj_format=flag_format)
    else:
      print(
          (
              'Please add the following identity to your Azure application'
              " '%s'\nIdentity: '%s'\n"
          )
          % (
              connection['azure'].get('federatedApplicationClientId'),
              connection['azure'].get('identity'),
          )
      )
  elif connection.get('azure'):
    obj = {
        'clientId': connection['azure'].get('clientId'),
        'application': connection['azure'].get('application'),
    }
    if flag_format in ['prettyjson', 'json']:
      _print_formatted_json_object(obj, obj_format=flag_format)
    else:
      print(
          (
              'Please create a Service Principal in your directory '
              "for appId: '%s',\n"
              "and perform role assignment to app: '%s' to allow BigQuery "
              'to access your Azure data. \n'
          )
          % (
              connection['azure'].get('clientId'),
              connection['azure'].get('application'),
          )
      )


def _format_labels(labels: Dict[str, str]) -> str:
  """Format a resource's labels for printing."""
  result_lines = []
  for key, value in labels.items():
    label_str = '%s:%s' % (key, value)
    result_lines.extend([label_str])
  return '\n'.join(result_lines)


def _format_table_reference(
    table: bq_id_utils.ApiClientHelper.TableReference,
) -> str:
  return '%s:%s.%s' % (
      table['projectId'],
      table['datasetId'],
      table['tableId'],
  )


def _format_resource_tags(tags: Dict[str, str]) -> str:
  """Format a resource's tags for printing."""
  result_lines = ['{}:{}'.format(key, value) for key, value in tags.items()]
  return '\n'.join(result_lines)


def _format_standard_sql_fields(standard_sql_fields) -> str:
  """Returns a string with standard_sql_fields.

  Currently only supports printing primitive field types and repeated fields.
  Args:
    standard_sql_fields: A list of standard sql fields.

  Returns:
    The formatted standard sql fields.
  """
  lines = []
  for field in standard_sql_fields:
    if field['type']['typeKind'] == 'ARRAY':
      field_type = field['type']['arrayElementType']['typeKind']
    else:
      field_type = field['type']['typeKind']
    entry = '|- %s: %s' % (field['name'], field_type.lower())
    if field['type']['typeKind'] == 'ARRAY':
      entry += ' (repeated)'
    lines.extend([entry])
  return '\n'.join(lines)


def format_time(secs: float) -> str:
  return time.strftime('%d %b %H:%M:%S', time.localtime(secs))


def format_time_from_proto_timestamp_json_string(json_string: str) -> str:
  """Converts google.protobuf.Timestamp formatted string to BQ format."""
  parsed_datetime = datetime.datetime.strptime(
      json_string, '%Y-%m-%dT%H:%M:%S.%fZ'
  )
  seconds = (parsed_datetime - datetime.datetime(1970, 1, 1)).total_seconds()
  return format_time(seconds)


StringReference: TypeAlias = str  # eg. 'project:dataset.routine'
ResourceType: TypeAlias = str  # eg. 'ROUTINE' or 'All ROUTINES in DATASET'
# Conditions is used as a key for the dictionary of ACL entries that is printed.
# eg. (('title', 'Expires_2024'),
# ('description', 'Expires at noon on 2024-12-31'),
# ('expression', "request.time <timestamp('2024-12-31T12:00:00Z')"))
Conditions: TypeAlias = Tuple[Tuple[str, str], Tuple[str, str], Tuple[str, str]]
ResourceTypeAndConditions: TypeAlias = Tuple[ResourceType, Conditions]
DatasetAccess: TypeAlias = List[Dict[str, Union[Dict[str, str], str]]]


def format_acl(acl: DatasetAccess) -> str:
  """Format a server-returned ACL for printing."""

  acl_entries: Dict[ResourceTypeAndConditions, List[StringReference]] = (
      collections.defaultdict(list)
  )
  for entry in acl:
    entry = entry.copy()
    view = cast(Dict[str, str], entry.pop('view', None))
    dataset = cast(Dict[str, Dict[str, str]], entry.pop('dataset', None))
    routine = cast(Dict[str, str], entry.pop('routine', None))
    role = cast(str, entry.pop('role', None))
    if view:
      acl_entries['VIEW', ()].append(
          '%s:%s.%s'
          % (view.get('projectId'), view.get('datasetId'), view.get('tableId'))
      )
    elif dataset:
      dataset_reference = cast(Dict[str, str], dataset.get('dataset'))
      for target in dataset.get('targetTypes'):
        acl_entries['All ' + target + ' in DATASET', ()].append(
            '%s:%s'
            % (
                dataset_reference.get('projectId'),
                dataset_reference.get('datasetId'),
            )
        )
    elif routine:
      routine_reference = str(
          bq_id_utils.ApiClientHelper.RoutineReference(**routine)
      )
      if role:
        acl_entries[role, ()].append('ROUTINE: %s' % routine_reference)
      else:
        acl_entries['ROUTINE', ()].append(routine_reference)
    else:
      condition = cast(Dict[str, str], entry.pop('condition', None))
      if not role or len(list(entry.values())) != 1:
        raise bq_error.BigqueryInterfaceError(
            'Invalid ACL returned by server: %s' % acl, {}, []
        )
      if condition:
        acl_entries[(role, tuple(condition.items()))].extend(entry.values())
      else:
        acl_entries[role, ()].extend(entry.values())
  # Show a couple things first.
  original_roles = {
      'OWNER': 'Owners',
      'WRITER': 'Writers',
      'READER': 'Readers',
      'VIEW': 'Authorized Views',
  }
  result_lines = []
  for role, name in original_roles.items():
    members = acl_entries.pop((role, ()), None)
    if members:
      result_lines.append('%s:' % name)
      result_lines.append(',\n'.join('  %s' % m for m in sorted(members)))
  # Show everything else.
  for (role, condition), members in sorted(acl_entries.items()):
    if role in original_roles:
      result_lines.append('%s:' % original_roles[role])
    else:
      result_lines.append('%s:' % role)
    result_lines.append(',\n'.join('  %s' % m for m in sorted(members)))
    if condition:
      result_lines.append('    condition:')
      result_lines.append(
          '\n'.join(
              '      %s: %s' % (key, value)
              for key, value in dict(condition).items()
          )
      )
  return '\n'.join(result_lines)


def format_schema(schema) -> str:
  """Format a schema for printing."""

  def print_fields(fields, indent=0) -> List[str]:
    """Print all fields in a schema, recurring as necessary."""
    lines = []
    for field in fields:
      prefix = '|  ' * indent
      junction = '|' if field.get('type', 'STRING') != 'RECORD' else '+'
      entry = '%s- %s: %s' % (
          junction,
          field['name'],
          field.get('type', 'STRING').lower(),
      )
      # Print type parameters.
      if 'maxLength' in field:
        entry += '(%s)' % (field['maxLength'])
      elif 'precision' in field:
        if 'scale' in field:
          entry += '(%s, %s)' % (field['precision'], field['scale'])
        else:
          entry += '(%s)' % (field['precision'])
        if 'roundingMode' in field:
          entry += ' options(rounding_mode="%s")' % (field['roundingMode'])
      # Print type mode.
      if field.get('mode', 'NULLABLE') != 'NULLABLE':
        entry += ' (%s)' % (field['mode'].lower(),)
      lines.append(prefix + entry)
      if 'fields' in field:
        lines.extend(print_fields(field['fields'], indent + 1))
    return lines

  return '\n'.join(print_fields(schema.get('fields', [])))


def validate_print_format(print_format: str) -> None:
  if print_format not in [
      'show',
      'list',
      'view',
      'materialized_view',
      'make',
      'table_replica',
  ]:
    raise ValueError('Unknown format: %s' % (print_format,))


def configure_formatter(
    formatter: table_formatter.TableFormatter,
    reference_type: Type[bq_id_utils.ApiClientHelper.Reference],
    print_format: bq_consts.CustomPrintFormat = 'list',
    object_info=None,
):
  """Configure a formatter for a given reference type.

  If print_format is 'show', configures the formatter with several
  additional fields (useful for printing a single record).

  Arguments:
    formatter: TableFormatter object to configure.
    reference_type: Type of object this formatter will be used with.
    print_format: Either 'show' or 'list' to control what fields are included.
    object_info: Resource dict to format.

  Raises:
    ValueError: If reference_type or format is unknown.
  """
  validate_print_format(print_format)
  if reference_type == bq_id_utils.ApiClientHelper.JobReference:
    if print_format == 'list':
      formatter.AddColumns(('jobId',))
    formatter.AddColumns((
        'Job Type',
        'State',
        'Start Time',
        'Duration',
    ))
    if print_format == 'show':
      formatter.AddColumns(('User Email',))
      formatter.AddColumns(('Bytes Processed',))
      formatter.AddColumns(('Bytes Billed',))
      formatter.AddColumns(('Billing Tier',))
      formatter.AddColumns(('Labels',))
  elif reference_type == bq_id_utils.ApiClientHelper.ProjectReference:
    if print_format == 'list':
      formatter.AddColumns(('projectId',))
    formatter.AddColumns(('friendlyName',))
  elif reference_type == bq_id_utils.ApiClientHelper.DatasetReference:
    if print_format == 'list':
      formatter.AddColumns(('datasetId',))
    if print_format == 'show':
      formatter.AddColumns((
          'Last modified',
          'ACLs',
      ))
      formatter.AddColumns(('Labels',))
      add_tags = 'tags' in object_info
      add_tags = add_tags or 'resource_tags' in object_info
      if add_tags:
        formatter.AddColumns(('Tags',))
      if 'defaultEncryptionConfiguration' in object_info:
        formatter.AddColumns(('kmsKeyName',))
      if 'type' in object_info:
        formatter.AddColumns(('Type',))
      if 'linkedDatasetSource' in object_info:
        formatter.AddColumns(('Source dataset',))
      if 'maxTimeTravelHours' in object_info:
        formatter.AddColumns(('Max time travel (Hours)',))
  elif reference_type == bq_id_utils.ApiClientHelper.TransferConfigReference:
    if print_format == 'list':
      formatter.AddColumns(('name',))
      formatter.AddColumns(('displayName',))
      formatter.AddColumns(('dataSourceId',))
      formatter.AddColumns(('state',))
    if print_format == 'show':
      for key in object_info.keys():
        if key != 'name':
          formatter.AddColumns((key,))
  elif reference_type == bq_id_utils.ApiClientHelper.TransferRunReference:
    if print_format == 'show':
      for column in _COLUMNS_TO_INCLUDE_FOR_TRANSFER_RUN:
        if column != 'name':
          formatter.AddColumns((column,))
    elif print_format == 'list':
      for column in _COLUMNS_TO_INCLUDE_FOR_TRANSFER_RUN:
        formatter.AddColumns((column,))
    elif print_format == 'make':
      for column in _COLUMNS_TO_INCLUDE_FOR_TRANSFER_RUN:
        if column not in (_COLUMNS_EXCLUDED_FOR_MAKE_TRANSFER_RUN):
          formatter.AddColumns((column,))
  elif reference_type == bq_id_utils.ApiClientHelper.TransferLogReference:
    formatter.AddColumns(('messageText',))
    formatter.AddColumns(('messageTime',))
    formatter.AddColumns(('severity',))
  elif reference_type == bq_id_utils.ApiClientHelper.NextPageTokenReference:
    formatter.AddColumns(('nextPageToken',))
  elif reference_type == bq_id_utils.ApiClientHelper.ModelReference:
    if print_format == 'list':
      formatter.AddColumns(('Id', 'Model Type', 'Labels', 'Creation Time'))
    if print_format == 'show':
      formatter.AddColumns((
          'Id',
          'Model Type',
          'Feature Columns',
          'Label Columns',
          'Labels',
          'Creation Time',
          'Expiration Time',
      ))
      if 'encryptionConfiguration' in object_info:
        formatter.AddColumns(('kmsKeyName',))
  elif reference_type == bq_id_utils.ApiClientHelper.RoutineReference:
    if print_format == 'list':
      formatter.AddColumns((
          'Id',
          'Routine Type',
          'Language',
          'Creation Time',
          'Last Modified Time',
      ))
      formatter.AddColumns(('Is Remote',))
    if print_format == 'show':
      formatter.AddColumns((
          'Id',
          'Routine Type',
          'Language',
          'Signature',
          'Definition',
          'Creation Time',
          'Last Modified Time',
      ))
      if 'remoteFunctionOptions' in object_info:
        formatter.AddColumns((
            'Remote Function Endpoint',
            'Connection',
            'User Defined Context',
        ))
      if 'sparkOptions' in object_info:
        formatter.AddColumns((
            'Connection',
            'Runtime Version',
            'Container Image',
            'Properties',
            'Main File URI',
            'Main Class',
            'PyFile URIs',
            'Jar URIs',
            'File URIs',
            'Archive URIs',
        ))
      if 'pythonOptions' in object_info:
        formatter.AddColumns((
            'Entry Point',
            'Packages',
        ))
      if 'externalRuntimeOptions' in object_info:
        formatter.AddColumns((
            'Connection',
            'Runtime Version',
            'Container Memory',
            'Container CPU',
        ))
  elif reference_type == bq_id_utils.ApiClientHelper.RowAccessPolicyReference:
    if print_format == 'list' or print_format == 'show':
      formatter.AddColumns((
          'Id',
          'Filter Predicate',
          'Grantees',
          'Creation Time',
          'Last Modified Time',
      ))
  elif reference_type == bq_id_utils.ApiClientHelper.TableReference:
    if print_format == 'list':
      formatter.AddColumns((
          'tableId',
          'Type',
      ))
      formatter.AddColumns(('Labels', 'Time Partitioning', 'Clustered Fields'))
    if print_format == 'show':
      use_default = True
      if object_info is not None:
        if object_info['type'] == 'VIEW':
          formatter.AddColumns(
              ('Last modified', 'Schema', 'Type', 'Expiration')
          )
          use_default = False
        elif object_info['type'] == 'EXTERNAL':
          formatter.AddColumns(
              ('Last modified', 'Schema', 'Type', 'Total URIs', 'Expiration')
          )
          use_default = False
        elif 'snapshotDefinition' in object_info:
          formatter.AddColumns(('Base Table', 'Snapshot TimeStamp'))
        elif 'cloneDefinition' in object_info:
          formatter.AddColumns(('Base Table', 'Clone TimeStamp'))
      if use_default:
        # Other potentially available columns are: 'Long-Term Logical Bytes',
        # 'Active Logical Bytes', 'Total Partitions', 'Active Physical Bytes',
        # 'Long-Term Physical Bytes', 'Time Travel Bytes'.
        formatter.AddColumns((
            'Last modified',
            'Schema',
            'Total Rows',
            'Total Bytes',
            'Expiration',
            'Time Partitioning',
            'Clustered Fields',
            'Total Logical Bytes',
            'Total Physical Bytes',
        ))
      formatter.AddColumns(('Labels',))
      if 'encryptionConfiguration' in object_info:
        formatter.AddColumns(('kmsKeyName',))
      if 'resourceTags' in object_info:
        formatter.AddColumns(('Tags',))
    if print_format == 'view':
      formatter.AddColumns(('Query',))
    if print_format == 'materialized_view':
      formatter.AddColumns((
          'Query',
          'Enable Refresh',
          'Refresh Interval Ms',
          'Last Refresh Time'
      ))
    if print_format == 'table_replica':
      formatter.AddColumns((
          'Type',
          'Last modified',
          'Schema',
          'Source Table',
          'Source Last Refresh Time',
          'Replication Interval Seconds',
          'Replication Status',
          'Replication Error',
      ))
  elif reference_type == bq_id_utils.ApiClientHelper.EncryptionServiceAccount:
    formatter.AddColumns(list(object_info.keys()))
  elif reference_type == bq_id_utils.ApiClientHelper.ReservationReference:
    shared_columns = (
        'name',
        'slotCapacity',
        'targetJobConcurrency',
        'ignoreIdleSlots',
        'creationTime',
        'updateTime',
        'multiRegionAuxiliary',
        'edition',
        'autoscaleMaxSlots',
        'autoscaleCurrentSlots',
        'maxSlots',
        'scalingMode',
        'reservationGroup',
    )
    formatter.AddColumns(shared_columns)
  elif (
      reference_type == bq_id_utils.ApiClientHelper.CapacityCommitmentReference
  ):
    formatter.AddColumns((
        'name',
        'slotCount',
        'plan',
        'renewalPlan',
        'state',
        'commitmentStartTime',
        'commitmentEndTime',
        'multiRegionAuxiliary',
        'edition',
        'isFlatRate',
    ))
  elif (
      reference_type
      == bq_id_utils.ApiClientHelper.ReservationAssignmentReference
  ):
    formatter.AddColumns(('name', 'jobType', 'assignee'))
  elif reference_type == bq_id_utils.ApiClientHelper.ReservationGroupReference:
    formatter.AddColumns(('name',))
  elif reference_type == bq_id_utils.ApiClientHelper.ConnectionReference:
    formatter.AddColumns((
        'name',
        'friendlyName',
        'description',
        'Last modified',
        'type',
        'hasCredential',
        'properties',
    ))
  else:
    raise ValueError('Unknown reference type: %s' % (reference_type.__name__,))


def format_info_by_type(
    object_info, object_type: Type[bq_id_utils.ApiClientHelper.Reference]
):
  """Format a single object_info (based on its 'kind' attribute)."""
  if object_type == bq_id_utils.ApiClientHelper.JobReference:
    return format_job_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.ProjectReference:
    return format_project_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.DatasetReference:
    return format_dataset_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.TableReference:
    return format_table_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.ModelReference:
    return format_model_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.RoutineReference:
    return format_routine_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.RowAccessPolicyReference:
    return format_row_access_policy_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.TransferConfigReference:
    return format_transfer_config_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.TransferRunReference:
    return format_transfer_run_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.TransferLogReference:
    return format_transfer_log_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.EncryptionServiceAccount:
    return object_info
  elif issubclass(
      object_type, bq_id_utils.ApiClientHelper.ReservationReference
  ):
    return format_reservation_info(reservation=object_info)
  elif issubclass(
      object_type, bq_id_utils.ApiClientHelper.CapacityCommitmentReference
  ):
    return format_capacity_commitment_info(object_info)
  elif issubclass(
      object_type, bq_id_utils.ApiClientHelper.ReservationAssignmentReference
  ):
    return format_reservation_assignment_info(object_info)
  elif issubclass(
      object_type, bq_id_utils.ApiClientHelper.ReservationGroupReference
  ):
    return format_reservation_group_info(object_info)
  elif object_type == bq_id_utils.ApiClientHelper.ConnectionReference:
    return format_connection_info(object_info)
  else:
    raise ValueError('Unknown object type: %s' % (object_type,))


def format_job_info(job_info):
  """Prepare a job_info for printing.

  Arguments:
    job_info: Job dict to format.

  Returns:
    The new job_info.
  """
  result = job_info.copy()
  reference = bq_processor_utils.ConstructObjectReference(result)
  result.update(dict(reference))
  stats = result.get('statistics', {})

  result['Job Type'] = bq_processor_utils.GetJobTypeName(result)

  result['State'] = result['status']['state']
  if 'user_email' in result:
    result['User Email'] = result['user_email']
  if result['State'] == 'DONE':
    try:
      bq_client_utils.RaiseIfJobError(result)
      result['State'] = 'SUCCESS'
    except bq_error.BigqueryError:
      result['State'] = 'FAILURE'

  if 'startTime' in stats:
    start = int(stats['startTime']) / 1000
    if 'endTime' in stats:
      duration_seconds = int(stats['endTime']) / 1000 - start
      result['Duration'] = str(datetime.timedelta(seconds=duration_seconds))
    result['Start Time'] = format_time(start)


  session_id = bq_processor_utils.GetSessionId(job_info)
  if session_id:
    result['Session Id'] = session_id

  query_stats = stats.get('query', {})
  if 'totalBytesProcessed' in query_stats:
    result['Bytes Processed'] = query_stats['totalBytesProcessed']
  if 'totalBytesBilled' in query_stats:
    result['Bytes Billed'] = query_stats['totalBytesBilled']
  if 'billingTier' in query_stats:
    result['Billing Tier'] = query_stats['billingTier']
  config = result.get('configuration', {})
  if 'labels' in config:
    result['Labels'] = _format_labels(config['labels'])
  if 'numDmlAffectedRows' in query_stats:
    result['Affected Rows'] = query_stats['numDmlAffectedRows']
  if 'ddlOperationPerformed' in query_stats:
    result['DDL Operation Performed'] = query_stats['ddlOperationPerformed']
  if 'ddlTargetTable' in query_stats:
    result['DDL Target Table'] = dict(query_stats['ddlTargetTable'])
  if 'ddlTargetRoutine' in query_stats:
    result['DDL Target Routine'] = dict(query_stats['ddlTargetRoutine'])
  if 'ddlTargetRowAccessPolicy' in query_stats:
    result['DDL Target Row Access Policy'] = dict(
        query_stats['ddlTargetRowAccessPolicy']
    )
  if 'ddlAffectedRowAccessPolicyCount' in query_stats:
    result['DDL Affected Row Access Policy Count'] = query_stats[
        'ddlAffectedRowAccessPolicyCount'
    ]
  if 'statementType' in query_stats:
    result['Statement Type'] = query_stats['statementType']
    if query_stats['statementType'] == 'ASSERT':
      result['Assertion'] = True
  if 'defaultConnectionStats' in query_stats:
    result['Default Connection Stats'] = dict(
        query_stats['defaultConnectionStats']
    )
  return result


def format_project_info(project_info):
  """Prepare a project_info for printing.

  Arguments:
    project_info: Project dict to format.

  Returns:
    The new project_info.
  """
  result = project_info.copy()
  reference = bq_processor_utils.ConstructObjectReference(result)
  result.update(dict(reference))
  return result


def format_model_info(model_info):
  """Prepare a model for printing.

  Arguments:
    model_info: Model dict to format.

  Returns:
    A dictionary of model properties.
  """
  result = {}
  result['Id'] = model_info['modelReference']['modelId']
  result['Model Type'] = ''
  if 'modelType' in model_info:
    result['Model Type'] = model_info['modelType']
  if 'labels' in model_info:
    result['Labels'] = _format_labels(model_info['labels'])
  if 'creationTime' in model_info:
    result['Creation Time'] = format_time(
        int(model_info['creationTime']) / 1000
    )
  if 'expirationTime' in model_info:
    result['Expiration Time'] = format_time(
        int(model_info['expirationTime']) / 1000
    )
  if 'featureColumns' in model_info:
    result['Feature Columns'] = _format_standard_sql_fields(
        model_info['featureColumns']
    )
  if 'labelColumns' in model_info:
    result['Label Columns'] = _format_standard_sql_fields(
        model_info['labelColumns']
    )
  if 'encryptionConfiguration' in model_info:
    result['kmsKeyName'] = model_info['encryptionConfiguration']['kmsKeyName']
  return result


def format_routine_data_type(data_type) -> str:
  """Converts a routine data type to a pretty string representation.

  Arguments:
    data_type: Routine data type dict to format.

  Returns:
    A formatted string.
  """
  type_kind = data_type['typeKind']
  if type_kind == 'ARRAY':
    return '{}<{}>'.format(
        type_kind, format_routine_data_type(data_type['arrayElementType'])
    )
  elif type_kind == 'STRUCT':
    struct_fields = [
        '{} {}'.format(field['name'], format_routine_data_type(field['type']))
        for field in data_type['structType']['fields']
    ]
    return '{}<{}>'.format(type_kind, ', '.join(struct_fields))
  else:
    return type_kind


def format_routine_table_type(table_type) -> str:
  """Converts a routine table type to a pretty string representation.

  Arguments:
    table_type: Routine table type dict to format.

  Returns:
    A formatted string.
  """
  columns = [
      '{} {}'.format(column['name'], format_routine_data_type(column['type']))
      for column in table_type['columns']
  ]
  return 'TABLE<{}>'.format(', '.join(columns))


def format_routine_argument_info(routine_type, argument) -> str:
  """Converts a routine argument to a pretty string representation.

  Arguments:
    routine_type: The routine type of the corresponding routine. It's of string
      type corresponding to the string value of enum
      cloud.bigquery.v2.Routine.RoutineType.
    argument: Routine argument dict to format.

  Returns:
    A formatted string.
  """
  if 'dataType' in argument:
    display_type = format_routine_data_type(argument['dataType'])
  elif argument.get('argumentKind') == 'ANY_TYPE':
    display_type = 'ANY TYPE'
  elif routine_type == 'TABLE_VALUED_FUNCTION' and 'tableType' in argument:
    display_type = format_routine_table_type(argument['tableType'])
  elif (
      routine_type == 'TABLE_VALUED_FUNCTION'
      and argument.get('argumentKind') == 'ANY_TABLE'
  ):
    display_type = 'ANY TABLE'

  if 'name' in argument:
    argument_mode = ''
    if 'mode' in argument:
      argument_mode = argument['mode'] + ' '
    if (
        routine_type == 'AGGREGATE_FUNCTION'
        and 'isAggregate' in argument
        and not argument['isAggregate']
    ):
      return '{}{} {} {}'.format(
          argument_mode, argument['name'], display_type, 'NOT AGGREGATE'
      )
    else:
      return '{}{} {}'.format(argument_mode, argument['name'], display_type)
  else:
    return display_type


def format_routine_info(routine_info):
  """Prepare a routine for printing.

  Arguments:
    routine_info: Routine dict to format.

  Returns:
    A dictionary of routine properties.
  """
  result = {}
  result['Id'] = routine_info['routineReference']['routineId']
  result['Routine Type'] = routine_info['routineType']
  result['Language'] = routine_info.get('language', '')
  signature = '()'
  return_type = routine_info.get('returnType')
  return_table_type = routine_info.get('returnTableType')
  if 'arguments' in routine_info:
    argument_list = routine_info['arguments']
    signature = '({})'.format(
        ', '.join(
            format_routine_argument_info(routine_info['routineType'], argument)
            for argument in argument_list
        )
    )
  if return_type:
    signature = '{} -> {}'.format(
        signature, format_routine_data_type(return_type)
    )
  if return_table_type:
    signature = '{} -> {}'.format(
        signature, format_routine_table_type(return_table_type)
    )
  if return_type or return_table_type or ('arguments' in routine_info):
    result['Signature'] = signature
  if 'definitionBody' in routine_info:
    result['Definition'] = routine_info['definitionBody']
  if 'creationTime' in routine_info:
    result['Creation Time'] = format_time(
        int(routine_info['creationTime']) / 1000
    )
  if 'lastModifiedTime' in routine_info:
    result['Last Modified Time'] = format_time(
        int(routine_info['lastModifiedTime']) / 1000
    )
  result['Is Remote'] = 'No'
  if 'remoteFunctionOptions' in routine_info:
    result['Is Remote'] = 'Yes'
    result['Remote Function Endpoint'] = routine_info['remoteFunctionOptions'][
        'endpoint'
    ]
    result['Connection'] = routine_info['remoteFunctionOptions']['connection']
    result['User Defined Context'] = routine_info['remoteFunctionOptions'].get(
        'userDefinedContext', ''
    )
  if 'pythonOptions' in routine_info:
    result['Entry Point'] = routine_info['pythonOptions']['entryPoint']
    result['Packages'] = routine_info['pythonOptions'].get('packages')
    # if 'pythonOptions' is present, the routine is guaranteed to be a pythonUDF
    # and 'importedLibraries' value is used for imported .py library files.
    result['Libraries'] = routine_info.get('importedLibraries')
  if 'externalRuntimeOptions' in routine_info:
    result['Runtime Version'] = routine_info['externalRuntimeOptions'].get(
        'runtimeVersion'
    )
    result['Container Memory'] = routine_info['externalRuntimeOptions'].get(
        'containerMemory'
    )
    result['Container CPU'] = routine_info['externalRuntimeOptions'].get(
        'containerCpu'
    )
    result['Connection'] = routine_info['externalRuntimeOptions'].get(
        'runtimeConnection'
    )
    result['Max Batching Rows'] = routine_info['externalRuntimeOptions'].get(
        'maxBatchingRows'
    )
  if 'sparkOptions' in routine_info:
    spark_options = routine_info['sparkOptions']
    options = [
        ('connection', 'Connection'),
        ('runtimeVersion', 'Runtime Version'),
        ('containerImage', 'Container Image'),
        ('properties', 'Properties'),
        ('mainFileUri', 'Main File URI'),
        ('mainClass', 'Main Class'),
        ('pyFileUris', 'PyFile URIs'),
        ('jarUris', 'Jar URIs'),
        ('fileUris', 'File URIs'),
        ('archiveUris', 'Archive URIs'),
    ]
    for spark_key, result_key in options:
      if spark_key in spark_options:
        result[result_key] = spark_options[spark_key]
  return result


def format_row_access_policy_info(row_access_policy_info):
  """Prepare a row access policy for printing.

  Arguments:
    row_access_policy_info: Row access policy dict to format.

  Returns:
    A dictionary of row access policy properties.
  """
  result = {}
  result['Id'] = row_access_policy_info['rowAccessPolicyReference']['policyId']
  result['Filter Predicate'] = row_access_policy_info['filterPredicate']
  result['Grantees'] = ', '.join(row_access_policy_info['grantees'])
  if 'creationTime' in row_access_policy_info:
    result['Creation Time'] = format_time_from_proto_timestamp_json_string(
        row_access_policy_info['creationTime']
    )
  if 'lastModifiedTime' in row_access_policy_info:
    result['Last Modified Time'] = format_time_from_proto_timestamp_json_string(
        row_access_policy_info['lastModifiedTime']
    )
  return result


def format_dataset_info(dataset_info):
  """Prepare a dataset_info for printing.

  Arguments:
    dataset_info: Dataset dict to format.

  Returns:
    The new dataset_info.
  """
  result = dataset_info.copy()
  reference = bq_processor_utils.ConstructObjectReference(result)
  result.update(dict(reference))
  if 'lastModifiedTime' in result:
    result['Last modified'] = format_time(
        int(result['lastModifiedTime']) / 1000
    )
  if 'access' in result:
    result['ACLs'] = format_acl(result['access'])
  if 'labels' in result:
    result['Labels'] = _format_labels(result['labels'])
  if 'resourceTags' in result:
    result['Tags'] = _format_resource_tags(result['resourceTags'])
  if 'defaultEncryptionConfiguration' in result:
    result['kmsKeyName'] = result['defaultEncryptionConfiguration'][
        'kmsKeyName'
    ]
  if 'type' in result:
    result['Type'] = result['type']
    if result['type'] == 'LINKED' and 'linkedDatasetSource' in result:
      source_dataset = result['linkedDatasetSource']['sourceDataset']
      result['Source dataset'] = str(
          bq_id_utils.ApiClientHelper.DatasetReference.Create(**source_dataset)
      )
    if result['type'] == 'EXTERNAL' and 'externalDatasetReference' in result:
      external_dataset_reference = result['externalDatasetReference']
      if 'external_source' in external_dataset_reference:
        result['External source'] = external_dataset_reference[
            'external_source'
        ]
      if 'connection' in external_dataset_reference:
        result['Connection'] = external_dataset_reference['connection']
  if 'maxTimeTravelHours' in result:
    result['Max time travel (Hours)'] = result['maxTimeTravelHours']
  return result


def format_table_info(table_info):
  """Prepare a table_info for printing.

  Arguments:
    table_info: Table dict to format.

  Returns:
    The new table_info.
  """
  result = table_info.copy()
  reference = bq_processor_utils.ConstructObjectReference(result)
  result.update(dict(reference))
  if 'lastModifiedTime' in result:
    result['Last modified'] = format_time(
        int(result['lastModifiedTime']) / 1000
    )
  if 'schema' in result:
    result['Schema'] = format_schema(result['schema'])
  if 'numBytes' in result:
    result['Total Bytes'] = result['numBytes']
  if 'numTotalLogicalBytes' in result:
    result['Total Logical Bytes'] = result['numTotalLogicalBytes']
  if 'numLongTermLogicalBytes' in result:
    result['Long-Term Logical Bytes'] = result['numLongTermLogicalBytes']
  if 'numActiveLogicalBytes' in result:
    result['Active Logical Bytes'] = result['numActiveLogicalBytes']
  if 'numPartitions' in result:
    result['Total Partitions'] = result['numPartitions']
  if 'numTotalPhysicalBytes' in result:
    result['Total Physical Bytes'] = result['numTotalPhysicalBytes']
  if 'numActivePhysicalBytes' in result:
    result['Active Physical Bytes'] = result['numActivePhysicalBytes']
  if 'numLongTermPhysicalBytes' in result:
    result['Long-Term Physical Bytes'] = result['numLongTermPhysicalBytes']
  if 'numTimeTravelBytes' in result:
    result['Time Travel Bytes'] = result['numTimeTravelBytes']
  if 'numRows' in result:
    result['Total Rows'] = result['numRows']
  if 'expirationTime' in result:
    result['Expiration'] = format_time(int(result['expirationTime']) / 1000)
  if 'labels' in result:
    result['Labels'] = _format_labels(result['labels'])
  if 'resourceTags' in result:
    result['Tags'] = _format_resource_tags(result['resourceTags'])
  if 'timePartitioning' in result:
    if 'type' in result['timePartitioning']:
      result['Time Partitioning'] = result['timePartitioning']['type']
    else:
      result['Time Partitioning'] = 'DAY'
    extra_info = []
    if 'field' in result['timePartitioning']:
      partitioning_field = result['timePartitioning']['field']
      extra_info.append('field: %s' % partitioning_field)
    if 'expirationMs' in result['timePartitioning']:
      expiration_ms = int(result['timePartitioning']['expirationMs'])
      extra_info.append('expirationMs: %d' % (expiration_ms,))
    if extra_info:
      result['Time Partitioning'] += ' (%s)' % (', '.join(extra_info),)
  if 'clustering' in result:
    if 'fields' in result['clustering']:
      result['Clustered Fields'] = ', '.join(result['clustering']['fields'])
  if 'type' in result:
    result['Type'] = result['type']
    if 'view' in result and 'query' in result['view']:
      result['Query'] = result['view']['query']
    if 'materializedView' in result and 'query' in result['materializedView']:
      result['Query'] = result['materializedView']['query']
      if 'enableRefresh' in result['materializedView']:
        result['Enable Refresh'] = result['materializedView']['enableRefresh']
      if 'refreshIntervalMs' in result['materializedView']:
        result['Refresh Interval Ms'] = result['materializedView'][
            'refreshIntervalMs'
        ]
      if (
          'lastRefreshTime' in result['materializedView']
          and result['materializedView']['lastRefreshTime'] != '0'
      ):
        result['Last Refresh Time'] = format_time(
            int(result['materializedView']['lastRefreshTime']) / 1000
        )
    if 'tableReplicationInfo' in result:
      result['Source Table'] = _format_table_reference(
          result['tableReplicationInfo']['sourceTable']
      )
      result['Replication Interval Seconds'] = int(
          int(result['tableReplicationInfo']['replicationIntervalMs']) / 1000
      )
      result['Replication Status'] = result['tableReplicationInfo'][
          'replicationStatus'
      ]
      if 'replicatedSourceLastRefreshTime' in result['tableReplicationInfo']:
        result['Source Last Refresh Time'] = format_time(
            int(
                result['tableReplicationInfo'][
                    'replicatedSourceLastRefreshTime'
                ]
            )
            / 1000
        )
      if 'replicationError' in result['tableReplicationInfo']:
        result['Replication Error'] = result['tableReplicationInfo'][
            'replicationError'
        ]['message']
    if result['type'] == 'EXTERNAL':
      if 'externalDataConfiguration' in result:
        result['Total URIs'] = len(
            result['externalDataConfiguration']['sourceUris']
        )
  if (
      'encryptionConfiguration' in result
      and 'kmsKeyName' in result['encryptionConfiguration']
  ):
    result['kmsKeyName'] = result['encryptionConfiguration']['kmsKeyName']
  if 'snapshotDefinition' in result:
    result['Base Table'] = result['snapshotDefinition']['baseTableReference']
    result['Snapshot TimeStamp'] = format_time_from_proto_timestamp_json_string(
        result['snapshotDefinition']['snapshotTime']
    )
  if 'cloneDefinition' in result:
    result['Base Table'] = result['cloneDefinition']['baseTableReference']
    result['Clone TimeStamp'] = format_time_from_proto_timestamp_json_string(
        result['cloneDefinition']['cloneTime']
    )
  return result


def format_transfer_config_info(transfer_config_info):
  """Prepare transfer config info for printing.

  Arguments:
    transfer_config_info: transfer config info to format.

  Returns:
    The new transfer config info.
  """

  result = {}
  for key, value in transfer_config_info.items():
    result[key] = value

  return result


def format_transfer_log_info(transfer_log_info):
  """Prepare transfer log info for printing.

  Arguments:
    transfer_log_info: transfer log info to format.

  Returns:
    The new transfer config log.
  """
  result = {}
  for key, value in transfer_log_info.items():
    result[key] = value

  return result


def format_transfer_run_info(transfer_run_info):
  """Prepare transfer run info for printing.

  Arguments:
    transfer_run_info: transfer run info to format.

  Returns:
    The new transfer run info.
  """
  result = {}
  for key, value in transfer_run_info.items():
    if key in _COLUMNS_TO_INCLUDE_FOR_TRANSFER_RUN:
      result[key] = value
  return result


def format_reservation_info(
    reservation,
):
  """Prepare a reservation for printing.

  Arguments:
    reservation: reservation to format.

  Returns:
    A dictionary of reservation properties.
  """
  result = {}
  for key, value in reservation.items():
    if key == 'name':
      project_id, location, reservation_id = (
          bq_client_utils.ParseReservationPath(value)
      )
      reference = bq_id_utils.ApiClientHelper.ReservationReference.Create(
          projectId=project_id, location=location, reservationId=reservation_id
      )
      result[key] = reference.__str__()
    else:
      result[key] = value
  # Default values not passed along in the response.
  if 'slotCapacity' not in list(result.keys()):
    result['slotCapacity'] = '0'
  if 'ignoreIdleSlots' not in list(result.keys()):
    result['ignoreIdleSlots'] = 'False'
  if 'multiRegionAuxiliary' not in list(result.keys()):
    result['multiRegionAuxiliary'] = 'False'
  if 'concurrency' in list(result.keys()):
    # Rename concurrency we get from the API to targetJobConcurrency.
    result['targetJobConcurrency'] = result['concurrency']
    result.pop('concurrency', None)
  else:
    result['targetJobConcurrency'] = '0 (auto)'
  if 'autoscale' in list(result.keys()):
    if 'maxSlots' in result['autoscale']:
      result['autoscaleMaxSlots'] = result['autoscale']['maxSlots']
      result['autoscaleCurrentSlots'] = '0'
      if 'currentSlots' in result['autoscale']:
        result['autoscaleCurrentSlots'] = result['autoscale']['currentSlots']
    # The original 'autoscale' fields is not needed anymore now.
    result.pop('autoscale', None)
  return result


def format_reservation_group_info(
    reservation_group: Dict[str, Any],
) -> Dict[str, Any]:
  """Prepare a reservation group for printing.

  Arguments:
    reservation_group: reservation group to format.

  Returns:
    A dictionary of reservation group properties.
  """
  result = {}
  for key, value in reservation_group.items():
    if key == 'name':
      project_id, location, reservation_group_id = (
          bq_client_utils.ParseReservationGroupPath(value)
      )
      reference = bq_id_utils.ApiClientHelper.ReservationGroupReference.Create(
          projectId=project_id,
          location=location,
          reservationGroupId=reservation_group_id,
      )
      result[key] = reference.__str__()
    else:
      result[key] = value
  return result


def format_capacity_commitment_info(capacity_commitment):
  """Prepare a capacity commitment for printing.

  Arguments:
    capacity_commitment: capacity commitment to format.

  Returns:
    A dictionary of capacity commitment properties.
  """
  result = {}
  for key, value in capacity_commitment.items():
    if key == 'name':
      project_id, location, capacity_commitment_id = (
          bq_client_utils.ParseCapacityCommitmentPath(value)
      )
      reference = (
          bq_id_utils.ApiClientHelper.CapacityCommitmentReference.Create(
              projectId=project_id,
              location=location,
              capacityCommitmentId=capacity_commitment_id,
          )
      )
      result[key] = reference.__str__()
    else:
      result[key] = value
  # Default values not passed along in the response.
  if 'slotCount' not in list(result.keys()):
    result['slotCount'] = '0'
  if 'multiRegionAuxiliary' not in list(result.keys()):
    result['multiRegionAuxiliary'] = 'False'
  return result


def format_reservation_assignment_info(reservation_assignment):
  """Prepare a reservation_assignment for printing.

  Arguments:
    reservation_assignment: reservation_assignment to format.

  Returns:
    A dictionary of reservation_assignment properties.
  """
  result = {}
  for key, value in reservation_assignment.items():
    if key == 'name':
      project_id, location, reservation_id, reservation_assignment_id = (
          bq_client_utils.ParseReservationAssignmentPath(value)
      )
      reference = (
          bq_id_utils.ApiClientHelper.ReservationAssignmentReference.Create(
              projectId=project_id,
              location=location,
              reservationId=reservation_id,
              reservationAssignmentId=reservation_assignment_id,
          )
      )
      result[key] = reference.__str__()
    else:
      result[key] = value
  return result


def format_connection_info(connection):
  """Prepare a connection object for printing.

  Arguments:
    connection: connection to format.

  Returns:
    A dictionary of connection properties.
  """
  result = {}
  for key, value in connection.items():
    if key == 'name':
      project_id, location, connection_id = bq_client_utils.ParseConnectionPath(
          value
      )
      reference = bq_id_utils.ApiClientHelper.ConnectionReference.Create(
          projectId=project_id, location=location, connectionId=connection_id
      )
      result[key] = reference.__str__()
    elif key == 'lastModifiedTime':
      result['Last modified'] = format_time(int(value) / 1000)
    elif key in bq_processor_utils.CONNECTION_PROPERTY_TO_TYPE_MAP:
      result['type'] = bq_processor_utils.CONNECTION_PROPERTY_TO_TYPE_MAP.get(
          key
      )
      result['properties'] = json.dumps(value)
    else:
      result[key] = value
  result['hasCredential'] = connection.get('hasCredential', False)
  return result
