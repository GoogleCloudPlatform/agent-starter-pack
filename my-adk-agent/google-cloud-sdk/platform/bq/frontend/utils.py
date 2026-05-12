#!/usr/bin/env python
"""Python script for interacting with BigQuery."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import datetime
import functools
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Type

from absl import app
from absl import flags
import yaml

import table_formatter
import bq_utils
from clients import utils as bq_client_utils
from frontend import utils_flags
from frontend import utils_formatting
from utils import bq_consts
from utils import bq_error
from utils import bq_id_utils
from pyglib import stringutil

# pylint: disable=g-multiple-import
if sys.version_info < (3, 11):
  from typing_extensions import TypedDict, NotRequired  # pylint: disable=g-import-not-at-top
else:
  from typing import TypedDict, NotRequired  # pylint: disable=g-import-not-at-top
# pylint: enable=g-multiple-import

FLAGS = flags.FLAGS

PARQUET_LIST_INFERENCE_DESCRIPTION = (
    'Use schema inference specifically for Parquet LIST logical type.\n It'
    ' checks whether the LIST node is in the standard form as documented in:\n'
    ' https://github.com/apache/parquet-format/blob/master/LogicalTypes.md#lists\n'
    '  <optional | required> group <name> (LIST) {\n    repeated group list {\n'
    '      <optional | required> <element-type> element;\n    }\n  }\n Returns'
    ' the "element" node in list_element_node. The corresponding field for the'
    ' LIST node in the converted schema is treated as if the node has the'
    ' following schema:\n repeated <element-type> <name>\n This means nodes'
    ' "list" and "element" are omitted.\n\n Otherwise, the LIST node must be in'
    ' one of the forms described by the backward-compatibility rules as'
    ' documented in:\n'
    ' https://github.com/apache/parquet-format/blob/master/LogicalTypes.md#backward-compatibility-rules\n'
    ' <optional | required> group <name> (LIST) {\n   repeated <element-type>'
    ' <element-name>\n }\n Returns the <element-name> node in'
    ' list_element_node. The corresponding field for the LIST node in the'
    ' converted schema is treated as if the node has the following schema:\n'
    ' repeated <element-type> <name>\n This means the element node is omitted.'
)

CONNECTION_ID_PATTERN = re.compile(r'[\w-]+')
_RANGE_PATTERN = re.compile(r'^\[(\S+.+\S+), (\S+.+\S+)\)$')

_PARAMETERS_KEY = 'parameters'
_DEFAULT_STORAGE_LOCATION_URI_KEY = 'defaultStorageLocationUri'
_STORAGE_DESCRIPTOR_KEY = 'storageDescriptor'
_CONNECTION_ID_KEY = 'connectionId'

_DELIMITER_MAP = {
    'tab': '\t',
    '\\t': '\t',
}
_DDL_OPERATION_MAP = {
    'SKIP': 'Skipped',
    'CREATE': 'Created',
    'REPLACE': 'Replaced',
    'ALTER': 'Altered',
    'DROP': 'Dropped',
}


def ValidateGlobalFlags():
  """Validate combinations of global flag values."""
  if FLAGS.service_account and FLAGS.use_gce_service_account:
    raise app.UsageError(
        'Cannot specify both --service_account and --use_gce_service_account.'
    )



def ValidateAtMostOneSelected(*args: Any) -> bool:
  """Validates that at most one of the argument flags is selected.

  Args:
    *args: Each flag to be tested parsed in as a separate arg.

  Returns:
    True if more than 1 flag was selected, False if 1 or 0 were selected.
  """
  count = 0
  for arg in args:
    if arg:
      count += 1
  return count > 1


def ValidateAtMostOneSelectedAllowsDefault(*args: Any) -> bool:
  """Validates that at most one of the argument flags is selected.

    if the arg exists but the value is the default value,
    then it won't be counted. This is uself when users want to clear the
    value while setting another value. For example, 'update --arg1=0 --arg2=100'
    when arg1 and arg2 shouldn't coexist.

  Args:
    *args: Each flag to be tested parsed in as a separate arg.

  Returns:
    True if more than 1 flag was selected, False if 1 or 0 were selected.
  """
  count = 0
  for arg in args:
    if arg and type(arg)() != arg:
      count += 1
  return count > 1


def ProcessSource(description: str, source: str) -> Tuple[Any, Any]:
  """Process "source" parameter used for bq update and bq mk command.

  Args:
    description: Description of the dataset.
    source: source file path attached by "--source" parameter.

  Returns:
    new description if the source file updates the description, otherwise return
    the original description.
    acl if the source file updates the acl, otherwise return None.
  """
  acl = None
  if source is None:
    return (description, acl)
  if not os.path.exists(source):
    raise app.UsageError('Source file not found: %s' % (source,))
  if not os.path.isfile(source):
    raise app.UsageError('Source path is not a file: %s' % (source,))
  with open(source) as f:
    try:
      payload = json.load(f)
      if 'description' in payload:
        description = payload['description']
        logging.debug(
            'Both source file and description flag exist, using the value in'
            ' the source file.'
        )
      if 'access' in payload:
        acl = payload['access']
    except ValueError as e:
      raise app.UsageError(
          'Error decoding JSON schema from file %s: %s' % (source, e)
      )

  return (description, acl)


def PrintDryRunInfo(job):
  """Prints the dry run info."""
  if FLAGS.format in ['prettyjson', 'json']:
    bq_utils.PrintFormattedJsonObject(job)
    return
  # TODO: b/422281423 - Revert this check once server returns this field for
  # all dry run queries again.
  if 'totalBytesProcessed' not in job['statistics']['query']:
    print(
        'Query successfully validated. No information about number of bytes'
        ' processed. To see the full details of the job, run this query with'
        ' `--format=json` or `--format=prettyjson`.'
    )
    return
  num_bytes = job['statistics']['query']['totalBytesProcessed']
  num_bytes_accuracy = job['statistics']['query'].get(
      'totalBytesProcessedAccuracy', 'PRECISE'
  )
  if FLAGS.format == 'csv':
    print(num_bytes)
  else:
    if job['statistics']['query'].get('statementType', '') == 'LOAD_DATA':
      print(
          'Query successfully validated. Assuming the files are not modified, '
          'running this query will process %s files loading %s bytes of data.'
          % (
              job['statistics']['query']['loadQueryStatistics']['inputFiles'],
              job['statistics']['query']['loadQueryStatistics'][
                  'inputFileBytes'
              ],
          )
      )
    elif num_bytes_accuracy == 'PRECISE':
      print(
          'Query successfully validated. Assuming the tables are not modified, '
          'running this query will process %s bytes of data.' % (num_bytes,)
      )
    elif num_bytes_accuracy == 'LOWER_BOUND':
      print(
          'Query successfully validated. Assuming the tables are not modified, '
          'running this query will process lower bound of %s bytes of data.'
          % (num_bytes,)
      )
    elif num_bytes_accuracy == 'UPPER_BOUND':
      print(
          'Query successfully validated. Assuming the tables are not modified, '
          'running this query will process upper bound of %s bytes of data.'
          % (num_bytes,)
      )
    else:
      if job['statistics']['query']['statementType'] == 'CREATE_MODEL':
        print(
            'Query successfully validated. The number of bytes that will '
            'be processed by this query cannot be calculated automatically. '
            'More information about this can be seen in '
            'https://cloud.google.com/bigquery-ml/pricing#dry_run'
        )
      else:
        print(
            'Query successfully validated. Assuming the tables are not '
            'modified, running this query will process %s of data and the '
            'accuracy is unknown because of federated tables or clustered '
            'tables.' % (num_bytes,)
        )


def RawInput(message: str) -> str:
  try:
    return input(message)
  except EOFError:
    if sys.stdin.isatty():
      print('\nGot EOF; exiting.')
    else:
      print('\nGot EOF; exiting. Is your input from a terminal?')
    sys.exit(1)


def PromptWithDefault(message: str) -> str:
  """Prompts user with message, return key pressed or '' on enter."""
  if FLAGS.headless:
    print('Running --headless, accepting default for prompt: %s' % (message,))
    return ''
  return RawInput(message).lower()


def PromptYN(message: str) -> Optional[str]:
  """Prompts user with message, returning the key 'y', 'n', or '' on enter."""
  response = None
  while response not in ['y', 'n', '']:
    response = PromptWithDefault(message)
  return response


def NormalizeFieldDelimiter(field_delimiter: str) -> str:
  """Validates and returns the correct field_delimiter."""
  # The only non-string delimiter we allow is None, which represents
  # no field delimiter specified by the user.
  if field_delimiter is None:
    return field_delimiter

  # Allow TAB and \\t substitution.
  key = field_delimiter.lower()
  return _DELIMITER_MAP.get(key, field_delimiter)


def ValidateHivePartitioningOptions(hive_partitioning_mode):
  """Validates the string provided is one the API accepts.

  Should not receive None as an input, since that will fail the comparison.
  Args:
    hive_partitioning_mode: String representing which hive partitioning mode is
      requested.  Only 'AUTO' and 'STRINGS' are supported.
  """
  if hive_partitioning_mode not in ['AUTO', 'STRINGS', 'CUSTOM']:
    raise app.UsageError(
        'Only the following hive partitioning modes are supported: "AUTO", '
        '"STRINGS" and "CUSTOM"'
    )


def ParseLabels(labels: List[str]) -> Dict[str, str]:
  """Parses a list of user-supplied strings representing labels.

  Args:
    labels: A list of user-supplied strings representing labels.  It is expected
      to be in the format "key:value".

  Returns:
    A dict mapping label keys to label values.

  Raises:
    UsageError: Incorrect label arguments were supplied.
  """
  labels_dict = {}
  for key_value in labels:
    k, _, v = key_value.partition(':')
    k = k.strip()
    if k in labels_dict:
      raise app.UsageError('Cannot specify label key "%s" multiple times' % k)
    if k.strip():
      labels_dict[k.strip()] = v.strip()
  return labels_dict


def IsRangeBoundaryUnbounded(value: str) -> bool:
  return value.upper() == 'UNBOUNDED' or value.upper() == 'NULL'


def ParseRangeString(value: str) -> Optional[Tuple[str, str]]:
  match = _RANGE_PATTERN.match(value)
  if not match:
    return None
  start, end = match.groups()
  return start, end


class TablePrinter(object):
  """Base class for printing a table, with a default implementation."""

  def __init__(self, **kwds):
    super(TablePrinter, self).__init__()
    # Most extended classes will require state.
    for key, value in kwds.items():
      setattr(self, key, value)

  @staticmethod
  def _ValidateFields(fields, formatter):
    if isinstance(formatter, table_formatter.CsvFormatter):
      for field in fields:
        if field['type'].upper() == 'RECORD':
          raise app.UsageError(
              (
                  'Error printing table: Cannot print record '
                  'field "%s" in CSV format.'
              )
              % field['name']
          )
        if field.get('mode', 'NULLABLE').upper() == 'REPEATED':
          raise app.UsageError(
              (
                  'Error printing table: Cannot print repeated '
                  'field "%s" in CSV format.'
              )
              % (field['name'])
          )

  @staticmethod
  def _NormalizeRecord(field, value, use_full_timestamp):
    """Returns bq-specific formatting of a RECORD type."""
    result = collections.OrderedDict()
    for subfield, subvalue in zip(field.get('fields', []), value):
      result[subfield.get('name', '')] = TablePrinter.NormalizeField(
          subfield, subvalue, use_full_timestamp
      )
    return result

  @staticmethod
  def _NormalizeTimestamp(unused_field, value, use_full_timestamp):
    """Returns bq-specific formatting of a TIMESTAMP type."""
    try:
      if use_full_timestamp:
        return value
      else:
        date = datetime.datetime.fromtimestamp(
            0, tz=datetime.timezone.utc
        ) + datetime.timedelta(seconds=float(value))
        # Remove the extra timezone info "+00:00" at the end of the date.
        date = date.replace(tzinfo=None)
        # Our goal is the equivalent of '%Y-%m-%d %H:%M:%S' via strftime but that
        # doesn't work for dates with years prior to 1900.  Instead we zero out
        # fractional seconds then call isoformat with a space separator.
        date = date.replace(microsecond=0)
        return date.isoformat(' ')
    except (ValueError, OverflowError):
      return '<date out of range for display>'

  @staticmethod
  def _NormalizeRange(field, value, use_full_timestamp):
    """Returns bq-specific formatting of a RANGE type."""
    parsed = ParseRangeString(value)
    if parsed is None:
      return '<invalid range>'
    start, end = parsed

    if field.get('rangeElementType').get('type').upper() != 'TIMESTAMP':
      start = start.upper() if IsRangeBoundaryUnbounded(start) else start
      end = end.upper() if IsRangeBoundaryUnbounded(end) else end
      return '[%s, %s)' % (start, end)

    if IsRangeBoundaryUnbounded(start):
      normalized_start = start.upper()
    else:
      normalized_start = TablePrinter._NormalizeTimestamp(
          field, start, use_full_timestamp
      )
    if IsRangeBoundaryUnbounded(end):
      normalized_end = end.upper()
    else:
      normalized_end = TablePrinter._NormalizeTimestamp(
          field, end, use_full_timestamp
      )
    return '[%s, %s)' % (normalized_start, normalized_end)

  @staticmethod
  def NormalizeField(field, value, use_full_timestamp: bool):
    """Returns bq-specific formatting of a field."""
    if value is None:
      return None
    if field.get('mode', '').upper() == 'REPEATED':
      return [
          TablePrinter._NormalizeSingleValue(field, value, use_full_timestamp)
          for value in value
      ]
    return TablePrinter._NormalizeSingleValue(field, value, use_full_timestamp)

  @staticmethod
  def _NormalizeSingleValue(field, value, use_full_timestamp: bool):
    """Returns formatting of a single field value."""
    if field.get('type', '').upper() == 'RECORD':
      return TablePrinter._NormalizeRecord(field, value, use_full_timestamp)
    elif field.get('type', '').upper() == 'TIMESTAMP':
      return TablePrinter._NormalizeTimestamp(field, value, use_full_timestamp)
    elif field.get('type', '').upper() == 'RANGE':
      return TablePrinter._NormalizeRange(field, value, use_full_timestamp)
    return value

  @staticmethod
  def MaybeConvertToJson(value):
    """Converts dicts and lists to JSON; returns everything else as-is."""
    if isinstance(value, dict) or isinstance(value, list):
      return json.dumps(value, separators=(',', ':'), ensure_ascii=False)
    return value

  @staticmethod
  def FormatRow(fields, row, formatter, use_full_timestamp: bool):
    """Convert fields in a single row to bq-specific formatting."""
    values = [
        TablePrinter.NormalizeField(field, value, use_full_timestamp)
        for field, value in zip(fields, row)
    ]
    # Convert complex values to JSON if we're not already outputting as such.
    if not isinstance(formatter, table_formatter.JsonFormatter):
      values = map(TablePrinter.MaybeConvertToJson, values)
    # Convert NULL values to strings for CSV and non-JSON formats.
    if isinstance(formatter, table_formatter.CsvFormatter):
      values = ['' if value is None else value for value in values]
    elif not isinstance(formatter, table_formatter.JsonFormatter):
      values = ['NULL' if value is None else value for value in values]
    return values

  def PrintTable(self, fields, rows, use_full_timestamp: bool):
    formatter = utils_flags.get_formatter_from_flags(secondary_format='pretty')
    self._ValidateFields(fields, formatter)
    formatter.AddFields(fields)
    formatter.AddRows(
        TablePrinter.FormatRow(fields, row, formatter, use_full_timestamp)
        for row in rows
    )
    formatter.Print()


def CreateExternalTableDefinition(
    source_format,
    source_uris,
    schema,
    autodetect,
    connection_id=None,
    ignore_unknown_values=False,
    hive_partitioning_mode=None,
    hive_partitioning_source_uri_prefix=None,
    require_hive_partition_filter=None,
    use_avro_logical_types=False,
    parquet_enum_as_string=False,
    parquet_enable_list_inference=False,
    metadata_cache_mode=None,
    object_metadata=None,
    preserve_ascii_control_characters=False,
    reference_file_schema_uri=None,
    encoding=None,
    file_set_spec_type=None,
    null_marker=None,
    null_markers=None,
    time_zone=None,
    date_format=None,
    datetime_format=None,
    time_format=None,
    timestamp_format=None,
    source_column_match=None,
    parquet_map_target_type=None,
    timestamp_target_precision=None,
):
  """Creates an external table definition with the given URIs and the schema.

  Arguments:
    source_format: Format of source data. For CSV files, specify 'CSV'. For
      Google spreadsheet files, specify 'GOOGLE_SHEETS'. For newline-delimited
      JSON, specify 'NEWLINE_DELIMITED_JSON'. For Cloud Datastore backup,
      specify 'DATASTORE_BACKUP'. For Avro files, specify 'AVRO'. For Orc files,
      specify 'ORC'. For Parquet files, specify 'PARQUET'. For Iceberg tables,
      specify 'ICEBERG'.
    source_uris: Comma separated list of URIs that contain data for this table.
    schema: Either an inline schema or path to a schema file.
    autodetect: Indicates if format options, compression mode and schema be auto
      detected from the source data. True - means that autodetect is on, False
      means that it is off. None means format specific default: - For CSV it
      means autodetect is OFF - For JSON it means that autodetect is ON. For
      JSON, defaulting to autodetection is safer because the only option
      autodetected is compression. If a schema is passed, then the user-supplied
      schema is used.
    connection_id: The user flag with the same name defined for the _Load
      BigqueryCmd
    ignore_unknown_values:  Indicates if BigQuery should allow extra values that
      are not represented in the table schema. If true, the extra values are
      ignored. If false, records with extra columns are treated as bad records,
      and if there are too many bad records, an invalid error is returned in the
      job result. The default value is false. The sourceFormat property
      determines what BigQuery treats as an extra value: - CSV: Trailing columns
      - JSON: Named values that don't match any column names.
    hive_partitioning_mode: Enables hive partitioning.  AUTO indicates to
      perform automatic type inference.  STRINGS indicates to treat all hive
      partition keys as STRING typed.  No other values are accepted.
    hive_partitioning_source_uri_prefix: Shared prefix for all files until hive
      partitioning encoding begins.
    require_hive_partition_filter: The user flag with the same name defined for
      the _Load BigqueryCmd
    use_avro_logical_types: The user flag with the same name defined for the
      _Load BigqueryCmd
    parquet_enum_as_string: The user flag with the same name defined for the
      _Load BigqueryCmd
    parquet_enable_list_inference: The user flag with the same name defined for
      the _Load BigqueryCmd
    metadata_cache_mode: Enables metadata cache for an external table with a
      connection. Specify 'AUTOMATIC' to automatically refresh the cached
      metadata. Specify 'MANUAL' to stop the automatic refresh.
    object_metadata: Object Metadata Type.
    preserve_ascii_control_characters: The user flag with the same name defined
      for the _Load BigqueryCmd
    reference_file_schema_uri: The user flag with the same name defined for the
      _Load BigqueryCmd
    encoding: Encoding types for CSV files. Available options are: 'UTF-8',
      'ISO-8859-1', 'UTF-16BE', 'UTF-16LE', 'UTF-32BE', and 'UTF-32LE'. The
      default value is 'UTF-8'.
    file_set_spec_type: Set how to discover files given source URIs. Specify
      'FILE_SYSTEM_MATCH' (default behavior) to expand source URIs by listing
      files from the underlying object store. Specify
      'NEW_LINE_DELIMITED_MANIFEST' to parse the URIs as new line delimited
      manifest files, where each line contains a URI (No wild-card URIs are
      supported).
    null_marker: Specifies a string that represents a null value in a CSV file.
    null_markers: Specifies a list of strings that represent null values in a
      CSV file.
    time_zone: Specifies the time zone for a CSV or JSON file.
    date_format: Specifies the date format for a CSV or JSON file.
    datetime_format: Specifies the datetime format for a CSV or JSON file.
    time_format: Specifies the time format for a CSV or JSON file.
    timestamp_format: Specifies the timestamp format for a CSV or JSON file.
    source_column_match: Controls the strategy used to match loaded columns to
      the schema.
    parquet_map_target_type: Indicate the target type for parquet maps. If
      unspecified, we represent parquet maps as map {repeated key_value {key,
      value}}. This option can simplify this by omiting the key_value record if
      it's equal to ARRAY_OF_STRUCT.
    timestamp_target_precision: Precision (maximum number of total digits in
      base 10) for seconds of TIMESTAMP type.

  Returns:
    A python dictionary that contains a external table definition for the given
    format with the most common options set.
  """
  try:
    supported_formats = [
        'CSV',
        'NEWLINE_DELIMITED_JSON',
        'DATASTORE_BACKUP',
        'DELTA_LAKE',
        'AVRO',
        'ORC',
        'PARQUET',
        'GOOGLE_SHEETS',
        'ICEBERG',
    ]

    if source_format not in supported_formats:
      raise app.UsageError('%s is not a supported format.' % source_format)

    external_table_def = {'sourceFormat': source_format}
    if file_set_spec_type is not None:
      external_table_def['fileSetSpecType'] = file_set_spec_type
    if metadata_cache_mode is not None:
      external_table_def['metadataCacheMode'] = metadata_cache_mode
    if time_zone is not None:
      external_table_def['timeZone'] = time_zone
    if date_format is not None:
      external_table_def['dateFormat'] = date_format
    if datetime_format is not None:
      external_table_def['datetimeFormat'] = datetime_format
    if time_format is not None:
      external_table_def['timeFormat'] = time_format
    if timestamp_format is not None:
      external_table_def['timestampFormat'] = timestamp_format
    if object_metadata is not None:
      supported_obj_metadata_types = ['DIRECTORY', 'SIMPLE']

      if object_metadata not in supported_obj_metadata_types:
        raise app.UsageError(
            '%s is not a supported Object Metadata Type.' % object_metadata
        )

      external_table_def['sourceFormat'] = None
      external_table_def['objectMetadata'] = object_metadata
    if timestamp_target_precision is not None:
      external_table_def['timestampTargetPrecision'] = timestamp_target_precision

    if external_table_def['sourceFormat'] == 'CSV':
      if autodetect:
        external_table_def['autodetect'] = True
        external_table_def['csvOptions'] = yaml.safe_load("""
            {
                "quote": '"',
                "encoding": "UTF-8"
            }
        """)
      else:
        external_table_def['csvOptions'] = yaml.safe_load("""
            {
                "allowJaggedRows": false,
                "fieldDelimiter": ",",
                "allowQuotedNewlines": false,
                "quote": '"',
                "skipLeadingRows": 0,
                "encoding": "UTF-8"
            }
        """)
      external_table_def['csvOptions'][
          'preserveAsciiControlCharacters'
      ] = preserve_ascii_control_characters
      external_table_def['csvOptions']['encoding'] = encoding or 'UTF-8'
      if null_marker is not None:
        external_table_def['csvOptions']['nullMarker'] = null_marker
      if null_markers is not None:
        external_table_def['csvOptions']['nullMarkers'] = null_markers
      if source_column_match is not None:
        external_table_def['csvOptions'][
            'sourceColumnMatch'
        ] = source_column_match
    elif external_table_def['sourceFormat'] == 'NEWLINE_DELIMITED_JSON':
      if autodetect is None or autodetect:
        external_table_def['autodetect'] = True
      external_table_def['jsonOptions'] = {'encoding': encoding or 'UTF-8'}
    elif external_table_def['sourceFormat'] == 'GOOGLE_SHEETS':
      if autodetect is None or autodetect:
        external_table_def['autodetect'] = True
      else:
        external_table_def['googleSheetsOptions'] = yaml.safe_load("""
            {
                "skipLeadingRows": 0
            }
        """)
    elif external_table_def['sourceFormat'] == 'AVRO':
      external_table_def['avroOptions'] = {
          'useAvroLogicalTypes': use_avro_logical_types
      }
      if reference_file_schema_uri is not None:
        external_table_def['referenceFileSchemaUri'] = reference_file_schema_uri
    elif external_table_def['sourceFormat'] == 'PARQUET':
      external_table_def['parquetOptions'] = {
          'enumAsString': parquet_enum_as_string,
          'enableListInference': parquet_enable_list_inference,
          'mapTargetType': parquet_map_target_type,
      }
      if reference_file_schema_uri is not None:
        external_table_def['referenceFileSchemaUri'] = reference_file_schema_uri
    elif external_table_def['sourceFormat'] == 'ORC':
      if reference_file_schema_uri is not None:
        external_table_def['referenceFileSchemaUri'] = reference_file_schema_uri
    elif (
        external_table_def['sourceFormat'] == 'ICEBERG'
        or external_table_def['sourceFormat'] == 'DELTA_LAKE'
    ):
      source_format = (
          'Iceberg'
          if external_table_def['sourceFormat'] == 'ICEBERG'
          else 'Delta Lake'
      )
      if autodetect is not None and not autodetect or schema:
        raise app.UsageError(
            'Cannot create %s table from user-specified schema.'
            % (source_format,)
        )
      # Always autodetect schema for ICEBERG from manifest
      external_table_def['autodetect'] = True
      if len(source_uris.split(',')) != 1:
        raise app.UsageError(
            'Must provide only one source_uri for %s table.' % (source_format,)
        )


    if ignore_unknown_values:
      external_table_def['ignoreUnknownValues'] = True


    if hive_partitioning_mode is not None:
      ValidateHivePartitioningOptions(hive_partitioning_mode)
      hive_partitioning_options = {}
      hive_partitioning_options['mode'] = hive_partitioning_mode
      if hive_partitioning_source_uri_prefix is not None:
        hive_partitioning_options['sourceUriPrefix'] = (
            hive_partitioning_source_uri_prefix
        )
      external_table_def['hivePartitioningOptions'] = hive_partitioning_options
      if require_hive_partition_filter:
        hive_partitioning_options['requirePartitionFilter'] = True

    if schema:
      fields = bq_client_utils.ReadSchema(schema)
      external_table_def['schema'] = {'fields': fields}

    if connection_id:
      external_table_def['connectionId'] = connection_id

    external_table_def['sourceUris'] = source_uris.split(',')

    return external_table_def

  except ValueError as e:
    raise app.UsageError(
        'Error occurred while creating table definition: %s' % e
    )


def GetExternalDataConfig(
    file_path_or_simple_spec,
    use_avro_logical_types=False,
    parquet_enum_as_string=False,
    parquet_enable_list_inference=False,
    metadata_cache_mode=None,
    object_metadata=None,
    preserve_ascii_control_characters=None,
    reference_file_schema_uri=None,
    file_set_spec_type=None,
    null_marker=None,
    null_markers=None,
    time_zone=None,
    date_format=None,
    datetime_format=None,
    time_format=None,
    timestamp_format=None,
    source_column_match=None,
    parquet_map_target_type=None,
    timestamp_target_precision=None,
):
  """Returns a ExternalDataConfiguration from the file or specification string.

  Determines if the input string is a file path or a string,
  then returns either the parsed file contents, or the parsed configuration from
  string. The file content is expected to be JSON representation of
  ExternalDataConfiguration. The specification is expected to be of the form
  schema@format=uri i.e. schema is separated from format and uri by '@'. If the
  uri itself contains '@' or '=' then the JSON file option should be used.
  "format=" can be omitted for CSV files.

  Raises:
    UsageError: when incorrect usage or invalid args are used.
  """
  maybe_filepath = os.path.expanduser(file_path_or_simple_spec)
  if os.path.isfile(maybe_filepath):
    try:
      with open(maybe_filepath) as external_config_file:
        return yaml.safe_load(external_config_file)
    except yaml.error.YAMLError as e:
      raise app.UsageError(
          'Error decoding YAML external table definition from file %s: %s'
          % (maybe_filepath, e)
      )
  else:
    source_format = 'CSV'
    schema = None
    connection_id = None
    error_msg = (
        'Error decoding external_table_definition. '
        'external_table_definition should either be the name of a '
        'JSON file or the text representation of an external table '
        'definition. Given:%s'
    ) % (file_path_or_simple_spec)

    parts = file_path_or_simple_spec.split('@')
    if len(parts) == 1:
      # Schema and connection are not specified.
      format_and_uri = parts[0]
    elif len(parts) == 2:
      # when there are 2 components, it can be:
      # 1. format=uri@connection_id.e.g csv=gs://bucket/file@us.conn1
      # 2. schema@format=uri        e.g.col1::INTEGER@csv=gs://bucket/file
      # if the first element is format=uri, then second element is connnection.
      # Else, the first is schema, second is format=uri.
      if parts[0].find('://') >= 0:
        # format=uri and connection specified.
        format_and_uri = parts[0]
        connection_id = parts[1]
      else:
        # Schema and format=uri are specified.
        schema = parts[0]
        format_and_uri = parts[1]
    elif len(parts) == 3:
      # Schema and connection both are specified
      schema = parts[0]
      format_and_uri = parts[1]
      connection_id = parts[2]
    else:
      raise app.UsageError(error_msg)

    separator_pos = format_and_uri.find('=')
    if separator_pos < 0:
      # Format is not specified
      uri = format_and_uri
    else:
      source_format = format_and_uri[0:separator_pos]
      uri = format_and_uri[separator_pos + 1 :]

    if not uri:
      raise app.UsageError(error_msg)
    # When using short notation for external table definition
    # autodetect is always performed.

    return CreateExternalTableDefinition(
        source_format,
        uri,
        schema,
        True,
        connection_id,
        use_avro_logical_types=use_avro_logical_types,
        parquet_enum_as_string=parquet_enum_as_string,
        parquet_enable_list_inference=parquet_enable_list_inference,
        metadata_cache_mode=metadata_cache_mode,
        object_metadata=object_metadata,
        preserve_ascii_control_characters=preserve_ascii_control_characters,
        reference_file_schema_uri=reference_file_schema_uri,
        file_set_spec_type=file_set_spec_type,
        null_marker=null_marker,
        null_markers=null_markers,
        time_zone=time_zone,
        date_format=date_format,
        datetime_format=datetime_format,
        time_format=time_format,
        timestamp_format=timestamp_format,
        source_column_match=source_column_match,
        parquet_map_target_type=parquet_map_target_type,
        timestamp_target_precision=timestamp_target_precision,
    )


def GetJson(
    file_path_or_json_string: str,
) -> Optional[Dict[str, Any]]:
  """Returns a JSON object from the file or a JSON string.

  Determines if the input string is a file path or a string,
  then returns either the parsed file contents, or the parsed JSON from
  string. The file content is expected to be a JSON string.

  Args:
    file_path_or_json_string: Path to the JSON file or a JSON string.

  Raises:
    UsageError: when incorrect usage or invalid args are used.
  """
  maybe_filepath = os.path.expanduser(file_path_or_json_string)
  if os.path.isfile(maybe_filepath):
    try:
      with open(maybe_filepath) as json_file:
        return json.load(json_file)
    except json.decoder.JSONDecodeError as e:
      raise app.UsageError(
          'Error decoding JSON from file %s: %s' % (maybe_filepath, e)
      )
  else:
    try:
      return json.loads(file_path_or_json_string)
    except json.decoder.JSONDecodeError as e:
      raise app.UsageError(
          'Error decoding JSON from string %s: %s'
          % (file_path_or_json_string, e)
      )


def UpdateExternalCatalogTableOptions(
    current_options: Dict[str, Any],
    external_options_str: str,
) -> Dict[str, Any]:
  """Updates the external catalog table options.

  Args:
    current_options: The current external catalog table options.
    external_options_str: The new external catalog table options as a JSON
      string or a file path.

  Returns:
    The updated external catalog table options.
  """
  # Clear the parameters if they are present in the existing options but not
  # in the new external catalog table options.
  if current_options.get(_PARAMETERS_KEY) is not None:
    current_options[_PARAMETERS_KEY] = {
        k: None for k in current_options[_PARAMETERS_KEY]
    }
  # Clear the storage descriptor if they are present in the existing options
  # but not in the new external catalog table options.
  if current_options.get(_STORAGE_DESCRIPTOR_KEY) is not None:
    current_options[_STORAGE_DESCRIPTOR_KEY] = {
        k: None for k in current_options[_STORAGE_DESCRIPTOR_KEY]
    }

  external_catalog_table_options_dict = GetJson(external_options_str)
  if _PARAMETERS_KEY in external_catalog_table_options_dict:
    current_options.setdefault(_PARAMETERS_KEY, {})
    current_options[_PARAMETERS_KEY].update(
        external_catalog_table_options_dict[_PARAMETERS_KEY]
    )
  else:
    current_options[_PARAMETERS_KEY] = None
  if _STORAGE_DESCRIPTOR_KEY in external_catalog_table_options_dict:
    current_options[_STORAGE_DESCRIPTOR_KEY] = (
        external_catalog_table_options_dict[_STORAGE_DESCRIPTOR_KEY]
    )
  else:
    current_options[_STORAGE_DESCRIPTOR_KEY] = None
  if _CONNECTION_ID_KEY in external_catalog_table_options_dict:
    current_options[_CONNECTION_ID_KEY] = external_catalog_table_options_dict[
        _CONNECTION_ID_KEY
    ]
  else:
    current_options[_CONNECTION_ID_KEY] = None
  return current_options


def UpdateExternalCatalogDatasetOptions(
    current_options: Dict[str, Any],
    external_options_str: str,
) -> Dict[str, Any]:
  """Updates the external catalog dataset options.

  Args:
    current_options: The current external catalog dataset options.
    external_options_str: The new external catalog dataset options as a JSON
      string or a file path.

  Returns:
    The updated external catalog dataset options.
  """
  # Clear the parameters if they are present in the existing dataset but not
  # in the new external catalog dataset options.
  if current_options.get(_PARAMETERS_KEY) is not None:
    current_options[_PARAMETERS_KEY] = {
        k: None for k in current_options[_PARAMETERS_KEY]
    }
  external_catalog_dataset_options_dict = GetJson(external_options_str)
  if _PARAMETERS_KEY in external_catalog_dataset_options_dict:
    current_options.setdefault(_PARAMETERS_KEY, {})
    for key, value in external_catalog_dataset_options_dict[
        _PARAMETERS_KEY
    ].items():
      current_options[_PARAMETERS_KEY][key] = value
  else:
    current_options[_PARAMETERS_KEY] = None
  if _DEFAULT_STORAGE_LOCATION_URI_KEY in external_catalog_dataset_options_dict:
    current_options[_DEFAULT_STORAGE_LOCATION_URI_KEY] = (
        external_catalog_dataset_options_dict[_DEFAULT_STORAGE_LOCATION_URI_KEY]
    )
  else:
    current_options[_DEFAULT_STORAGE_LOCATION_URI_KEY] = None
  return current_options


def PrintPageToken(page_token):
  """Prints the page token in the pretty format.

  Args:
    page_token: The dictionary mapping of pageToken with string 'nextPageToken'.
  """
  formatter = utils_flags.get_formatter_from_flags(secondary_format='pretty')
  utils_formatting.configure_formatter(
      formatter, bq_id_utils.ApiClientHelper.NextPageTokenReference
  )
  formatter.AddDict(page_token)
  formatter.Print()


def ParseTimePartitioning(
    partitioning_type=None,
    partitioning_expiration=None,
    partitioning_field=None,
    partitioning_minimum_partition_date=None,
    partitioning_require_partition_filter=None,
):
  """Parses time partitioning from the arguments.

  Args:
    partitioning_type: type for the time partitioning. Supported types are HOUR,
      DAY, MONTH, and YEAR. The default value is DAY when other arguments are
      specified, which generates one partition per day.
    partitioning_expiration: number of seconds to keep the storage for a
      partition. A negative value clears this setting.
    partitioning_field: if not set, the table is partitioned based on the
      loading time; if set, the table is partitioned based on the value of this
      field.
    partitioning_minimum_partition_date: lower boundary of partition date for
      field based partitioning table.
    partitioning_require_partition_filter: if true, queries on the table must
      have a partition filter so not all partitions are scanned.

  Returns:
    Time partitioning if any of the arguments is not None, otherwise None.

  Raises:
    UsageError: when failed to parse.
  """

  time_partitioning = {}
  key_type = 'type'
  key_expiration = 'expirationMs'
  key_field = 'field'
  key_minimum_partition_date = 'minimumPartitionDate'
  key_require_partition_filter = 'requirePartitionFilter'
  if partitioning_type is not None:
    time_partitioning[key_type] = partitioning_type
  if partitioning_expiration is not None:
    time_partitioning[key_expiration] = partitioning_expiration * 1000
  if partitioning_field is not None:
    time_partitioning[key_field] = partitioning_field
  if partitioning_minimum_partition_date is not None:
    if partitioning_field is not None:
      time_partitioning[key_minimum_partition_date] = (
          partitioning_minimum_partition_date
      )
    else:
      raise app.UsageError(
          'Need to specify --time_partitioning_field for '
          '--time_partitioning_minimum_partition_date.'
      )
  if partitioning_require_partition_filter is not None:
    if time_partitioning:
      time_partitioning[key_require_partition_filter] = (
          partitioning_require_partition_filter
      )

  if time_partitioning:
    if key_type not in time_partitioning:
      time_partitioning[key_type] = 'DAY'
    if (
        key_expiration in time_partitioning
        and time_partitioning[key_expiration] <= 0
    ):
      time_partitioning[key_expiration] = None
    return time_partitioning
  else:
    return None


def ParseFileSetSpecType(file_set_spec_type=None):
  """Parses the file set specification type from the arguments.

  Args:
    file_set_spec_type: specifies how to discover files given source URIs.

  Returns:
    file set specification type.
  Raises:
    UsageError: when an illegal value is passed.
  """
  if file_set_spec_type is None:
    return None
  valid_spec_types = ['FILE_SYSTEM_MATCH', 'NEW_LINE_DELIMITED_MANIFEST']
  if file_set_spec_type not in valid_spec_types:
    raise app.UsageError(
        'Error parsing file_set_spec_type, only FILE_SYSTEM_MATCH, '
        'NEW_LINE_DELIMITED_MANIFEST or no value are accepted'
    )
  return 'FILE_SET_SPEC_TYPE_' + file_set_spec_type


def ParseClustering(
    clustering_fields: Optional[str] = None,
) -> Optional[Dict[str, List[str]]]:
  """Parses clustering from the arguments.

  Args:
    clustering_fields: Comma-separated field names.

  Returns:
    Clustering if any of the arguments is not None, otherwise None. Special
    case if clustering_fields is passed in as an empty string instead of None,
    in which case we'll return {}, to support the scenario where user wants to
    update a table and remove the clustering spec.
  """

  if clustering_fields == '':  # pylint: disable=g-explicit-bool-comparison
    return {}
  elif clustering_fields is not None:
    return {'fields': clustering_fields.split(',')}
  else:
    return None


def ParseNumericTypeConversionMode(
    numeric_type_conversion_mode: Optional[str] = None,
) -> Optional[str]:
  """Parses the numeric type conversion mode from the arguments.

  Args:
    numeric_type_conversion_mode: specifies how the numeric values are handled
      when the value is out of scale.

  Returns:
    The conversion mode.

  Raises:
    UsageError: when an illegal value is passed.
  """

  if numeric_type_conversion_mode is None:
    return None
  elif numeric_type_conversion_mode == 'ROUND':
    return 'NUMERIC_TYPE_VALUE_ROUND'
  else:
    raise app.UsageError(
        'Error parsing numeric_type_conversion_mode, only ROUND or no value '
        'are accepted'
    )


def ParseRangePartitioning(range_partitioning_spec=None):
  """Parses range partitioning from the arguments.

  Args:
    range_partitioning_spec: specification for range partitioning in the format
      of field,start,end,interval.

  Returns:
    Range partitioning if range_partitioning_spec is not None, otherwise None.
  Raises:
    UsageError: when the spec fails to parse.
  """

  range_partitioning = {}
  key_field = 'field'
  key_range = 'range'
  key_range_start = 'start'
  key_range_end = 'end'
  key_range_interval = 'interval'

  if range_partitioning_spec is not None:
    parts = range_partitioning_spec.split(',')
    if len(parts) != 4:
      raise app.UsageError(
          'Error parsing range_partitioning. range_partitioning should be in '
          'the format of "field,start,end,interval"'
      )
    range_partitioning[key_field] = parts[0]
    range_spec = {}
    range_spec[key_range_start] = parts[1]
    range_spec[key_range_end] = parts[2]
    range_spec[key_range_interval] = parts[3]
    range_partitioning[key_range] = range_spec

  if range_partitioning:
    return range_partitioning
  else:
    return None


def IsSuccessfulDmlOrDdlJob(printable_job_info: str) -> bool:
  """Returns True iff the job is successful and is a DML/DDL query job."""
  return (
      'Affected Rows' in printable_job_info
      or 'DDL Operation Performed' in printable_job_info
  )


def MaybeGetSessionTempObjectName(
    dataset_id: str, object_id: str
) -> Optional[str]:
  """If we have a session temporary object, returns the user name of the object.

  Args:
    dataset_id: Dataset of object
    object_id: Id of object

  Returns:
    If the object is a session temp object, the name of the object after
    stripping out internal stuff such as session prefix and signature encodings.

    If the object is not a session temp object, the return value is None.
  """
  if not re.fullmatch('_[0-9a-f]{40}', dataset_id):
    return None  # Not an anonymous dataset

  session_prefix_regexp = (
      '_[0-9a-f]{8}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{12}_'
  )
  opt_signature_encoding_regexp = '(?:_b0a98f6_.*)?'
  match = re.fullmatch(
      session_prefix_regexp + '(.*?)' + opt_signature_encoding_regexp, object_id
  )
  if not match:
    return None  # No session prefix
  return match.group(1)


def PrintJobMessages(printable_job_info):
  """Prints additional info from a job formatted for printing.

  If the job had a fatal error, non-fatal warnings are not shown.

  If any error/warning does not have a 'message' key, printable_job_info must
  have 'jobReference' identifying the job.

  For DML queries prints number of affected rows.
  For DDL queries prints the performed operation and the target.
  """
  messages = GetJobMessagesForPrinting(printable_job_info)
  if messages:
    print(messages)


def GetJobMessagesForPrinting(printable_job_info):
  """Similar to _PrintJobMessages(), but returns a string, rather than printing."""
  result_lines = []

  job_ref = '(unknown)'  # Should never be seen, but beats a weird crash.
  if 'jobReference' in printable_job_info:
    job_ref = printable_job_info['jobReference']

  # For failing jobs, display the error but not any warnings, because those
  # may be more distracting than helpful.
  if printable_job_info['State'] == 'FAILURE':
    error_result = printable_job_info['status']['errorResult']
    error_ls = printable_job_info['status'].get('errors', [])
    error = bq_error.CreateBigqueryError(error_result, error_result, error_ls)
    result_lines.append(
        'Error encountered during job execution:\n%s\n' % (error,)
    )
  elif 'errors' in printable_job_info['status']:
    warnings = printable_job_info['status']['errors']
    result_lines.append((
        'Warning%s encountered during job execution:\n'
        % ('' if len(warnings) == 1 else 's')
    ))
    recommend_show = False
    for w in warnings:
      # Some warnings include detailed error messages, and some just
      # include programmatic error codes.  Some have a 'location'
      # separately, and some put it in the 'message' text.
      if 'message' not in w:
        recommend_show = True
      else:
        if 'location' in w:
          message = '[%s] %s' % (w['location'], w['message'])
        else:
          message = w['message']
        if message is not None:
          message = message.encode('utf-8')
        result_lines.append('%s\n' % message)
    if recommend_show:
      result_lines.append('Use "bq show -j %s" to view job warnings.' % job_ref)
  elif 'Affected Rows' in printable_job_info:
    result_lines.append(
        'Number of affected rows: %s\n' % printable_job_info['Affected Rows']
    )
  elif 'DDL Target Table' in printable_job_info:
    ddl_target_table = printable_job_info['DDL Target Table']
    project_id = ddl_target_table.get('projectId')
    dataset_id = ddl_target_table.get('datasetId')
    table_id = ddl_target_table.get('tableId')
    op = _DDL_OPERATION_MAP.get(
        printable_job_info.get('DDL Operation Performed')
    )
    # DDL Target Table is returned for both TABLE DDL and DROP ALL ROW ACCESS
    # POLICIES DDL statements.
    if project_id and dataset_id and table_id and op:
      if 'DDL Affected Row Access Policy Count' in printable_job_info:
        ddl_affected_row_access_policy_count = printable_job_info[
            'DDL Affected Row Access Policy Count'
        ]
        result_lines.append(
            '{op} {count} row access policies on table '
            '{project}.{dataset}.{table}\n'.format(
                op=op,
                count=ddl_affected_row_access_policy_count,
                project=project_id,
                dataset=dataset_id,
                table=table_id,
            )
        )
      elif (
          'Statement Type' in printable_job_info
          and 'INDEX' in printable_job_info['Statement Type']
      ):
        if 'SEARCH_INDEX' in printable_job_info['Statement Type']:
          result_lines.append(
              '%s search index on table %s.%s.%s\n'
              % (
                  stringutil.ensure_str(op),
                  stringutil.ensure_str(project_id),
                  stringutil.ensure_str(dataset_id),
                  stringutil.ensure_str(table_id),
              )
          )
        elif 'VECTOR_INDEX' in printable_job_info['Statement Type']:
          index_progress_instruction = ''
          if printable_job_info.get('DDL Operation Performed') in (
              'CREATE',
              'REPLACE',
          ):
            index_progress_instruction = (
                'Please query %s.%s.INFORMATION_SCHEMA to check the progress '
                ' of the index.\n'
            ) % (project_id, dataset_id)
          result_lines.append(
              '%s vector index on table %s.%s.%s\n%s'
              % (
                  stringutil.ensure_str(op),
                  stringutil.ensure_str(project_id),
                  stringutil.ensure_str(dataset_id),
                  stringutil.ensure_str(table_id),
                  stringutil.ensure_str(index_progress_instruction),
              )
          )
      else:
        result_lines.append(
            '%s %s.%s.%s\n'
            % (
                stringutil.ensure_str(op),
                stringutil.ensure_str(project_id),
                stringutil.ensure_str(dataset_id),
                stringutil.ensure_str(table_id),
            )
        )
        if 'Default Connection Stats' in printable_job_info:
          default_connection_stats = printable_job_info[
              'Default Connection Stats'
          ]
          location_id = job_ref['location']
          if 'provisioned' in default_connection_stats:
            if printable_job_info['Statement Type'] == 'CREATE_MODEL':
              target_type = 'model'
            else:
              target_type = 'table'
            result_lines.append(
                'Default connection created for %s [%s] in project [%s] in'
                ' region [%s]\n'
                % (
                    stringutil.ensure_str(target_type),
                    stringutil.ensure_str(table_id),
                    stringutil.ensure_str(project_id),
                    stringutil.ensure_str(location_id),
                )
            )
          if 'permissionUpdated' in default_connection_stats:
            result_lines.append(
                'Your IAM policy has been updated for the default connection\n'
            )
  elif 'DDL Target Routine' in printable_job_info:
    ddl_target_routine = printable_job_info['DDL Target Routine']
    project_id = ddl_target_routine.get('projectId')
    dataset_id = ddl_target_routine.get('datasetId')
    routine_id = ddl_target_routine.get('routineId')
    op = _DDL_OPERATION_MAP.get(
        printable_job_info.get('DDL Operation Performed')
    )
    temp_object_name = MaybeGetSessionTempObjectName(dataset_id, routine_id)
    if temp_object_name is not None:
      result_lines.append('%s temporary routine %s' % (op, temp_object_name))
    else:
      result_lines.append(
          '%s %s.%s.%s' % (op, project_id, dataset_id, routine_id)
      )
  elif 'DDL Target Row Access Policy' in printable_job_info:
    ddl_target_row_access_policy = printable_job_info[
        'DDL Target Row Access Policy'
    ]
    project_id = ddl_target_row_access_policy.get('projectId')
    dataset_id = ddl_target_row_access_policy.get('datasetId')
    table_id = ddl_target_row_access_policy.get('tableId')
    row_access_policy_id = ddl_target_row_access_policy.get('policyId')
    op = _DDL_OPERATION_MAP.get(
        printable_job_info.get('DDL Operation Performed')
    )
    if project_id and dataset_id and table_id and row_access_policy_id and op:
      result_lines.append(
          '{op} row access policy {policy} on table {project}.{dataset}.{table}'
          .format(
              op=op,
              policy=row_access_policy_id,
              project=project_id,
              dataset=dataset_id,
              table=table_id,
          )
      )
  elif 'Assertion' in printable_job_info:
    result_lines.append('Assertion successful')

  if 'Session Id' in printable_job_info:
    result_lines.append('In session: %s' % printable_job_info['Session Id'])

  return '\n'.join(result_lines)


def PrintObjectInfo(
    object_info,
    reference: bq_id_utils.ApiClientHelper.Reference,
    custom_format: bq_consts.CustomPrintFormat,
    print_reference: bool = True,
) -> None:
  """Prints the object with various formats."""
  # The JSON formats are handled separately so that they don't print
  # the record as a list of one record.
  if custom_format == 'schema':
    if 'schema' not in object_info or 'fields' not in object_info['schema']:
      raise app.UsageError('Unable to retrieve schema from specified table.')
    bq_utils.PrintFormattedJsonObject(object_info['schema']['fields'])
  elif FLAGS.format in ['prettyjson', 'json']:
    bq_utils.PrintFormattedJsonObject(object_info)
  elif FLAGS.format in [None, 'sparse', 'pretty']:
    formatter = utils_flags.get_formatter_from_flags()
    utils_formatting.configure_formatter(
        formatter,
        type(reference),
        print_format=custom_format,
        object_info=object_info,
    )
    object_info = utils_formatting.format_info_by_type(
        object_info, type(reference)
    )
    if object_info:
      formatter.AddDict(object_info)
    if reference.typename and print_reference:
      print('%s %s\n' % (reference.typename.capitalize(), reference))
    formatter.Print()
    print()
    if isinstance(reference, bq_id_utils.ApiClientHelper.JobReference):
      PrintJobMessages(object_info)
  else:
    formatter = utils_flags.get_formatter_from_flags()
    formatter.AddColumns(list(object_info.keys()))
    formatter.AddDict(object_info)
    formatter.Print()


def PrintObjectsArray(object_infos, objects_type):
  if FLAGS.format in ['prettyjson', 'json']:
    bq_utils.PrintFormattedJsonObject(object_infos)
  elif FLAGS.format in [None, 'sparse', 'pretty']:
    if not object_infos:
      return
    formatter = utils_flags.get_formatter_from_flags()
    if (
        objects_type
        is bq_id_utils.ApiClientHelper.ReservationAssignmentReference
    ):
      utils_formatting.configure_formatter(
          formatter, objects_type, print_format='list', object_info=object_infos
      )
    else:
      utils_formatting.configure_formatter(
          formatter, objects_type, print_format='list'
      )
    formatted_infos = list(
        map(
            functools.partial(
                utils_formatting.format_info_by_type,
                object_type=objects_type,
            ),
            object_infos,
        )
    )
    for info in formatted_infos:
      formatter.AddDict(info)
    formatter.Print()
  elif object_infos:
    formatter = utils_flags.get_formatter_from_flags()
    formatter.AddColumns(list(object_infos[0].keys()))
    for info in object_infos:
      formatter.AddDict(info)
    formatter.Print()


class ResourceMetadata(TypedDict):
  token: NotRequired[str] = None
  unreachable: NotRequired[List[str]] = None


def PrintObjectsArrayWithMetadata(
    objects_list: List[Any],
    objects_type: Type[bq_id_utils.ApiClientHelper.Reference],
    passed_flags: NamedTuple(
        'PassedFlags',
        [
            ('print_last_token', bool),
            ('print_unreachable', bool),
        ],
    ),
    objects_metadata: Optional[ResourceMetadata],
) -> None:
  """Prints the objects array with metadata configured to print using flags.

  If there is no `objects_metadata` passed in, then this function has the same
  behaviour as `PrintObjectsArray`.

  Different metadata can be printed by setting flags in `passed_flags`. With
  a `format` of 'sparse' or 'pretty' then nothing will be printed if no flags
  are set. With a format of 'prettyjson' or 'json' then the `objects_list`
  will be printed as a `results` value even if no flags are set to print
  metadata but if some are set, these will also be printed.

  Arguments:
    objects_list: The list of resources to print.
    objects_type: The type of the resources to be printed.
    passed_flags: Flags used to configure the printing behaviour.
    objects_metadata: Optional metadata to be printed.
  """
  if FLAGS.format in ['prettyjson', 'json']:
    if passed_flags.print_last_token or passed_flags.print_unreachable:
      json_object = {'results': objects_list}
      if passed_flags.print_last_token and 'token' in objects_metadata:
        json_object['token'] = objects_metadata['token']
      if passed_flags.print_unreachable and 'unreachable' in objects_metadata:
        json_object['unreachable'] = objects_metadata['unreachable']
    else:
      json_object = objects_list
    bq_utils.PrintFormattedJsonObject(json_object)
  elif FLAGS.format in [None, 'sparse', 'pretty']:
    PrintObjectsArray(objects_list, objects_type)
    if objects_metadata is None:
      return
    if passed_flags.print_last_token and 'token' in objects_metadata:
      print('\nNext token: ' + objects_metadata['token'])
    if passed_flags.print_unreachable and 'unreachable' in objects_metadata:
      print('\nUnreachable: ' + ', '.join(objects_metadata['unreachable']))


def ParseUdfResources(udf_resources):
  """Parses UDF resources from an array of resource URIs.

  Arguments:
    udf_resources: Array of udf resource URIs.

  Returns:
    Array of UDF resources parsed into the format expected by the BigQuery API
    client.
  """

  if udf_resources is None:
    return None
  inline_udf_resources = []
  external_udf_resources = []
  for uris in udf_resources:
    for uri in uris.split(','):
      if os.path.isfile(uri):
        with open(uri) as udf_file:
          inline_udf_resources.append(udf_file.read())
      else:
        if not uri.startswith('gs://'):
          raise app.UsageError(
              'Non-inline resources must be Google Cloud Storage (gs://) URIs'
          )
        external_udf_resources.append(uri)
  udfs = []
  if inline_udf_resources:
    for udf_code in inline_udf_resources:
      udfs.append({'inlineCode': udf_code})
  if external_udf_resources:
    for uri in external_udf_resources:
      udfs.append({'resourceUri': uri})
  return udfs


def ValidateDatasetName(dataset_name: str) -> None:
  """A regex to ensure the dataset name is valid.


  Arguments:
    dataset_name: string name of the dataset to be validated.

  Raises:
    UsageError: An error occurred due to invalid dataset string.
  """
  is_valid = re.fullmatch(r'[a-zA-Z0-9\_]{1,1024}', dataset_name)
  if not is_valid:
    raise app.UsageError(
        'Dataset name: %s is invalid, must be letters '
        '(uppercase or lowercase), numbers, and underscores up to '
        '1024 characters.' % dataset_name
    )


def ParseParameters(parameters):
  """Parses query parameters from an array of name:type:value.

  Arguments:
    parameters: An iterable of string-form query parameters: name:type:value.
      Name may be omitted to indicate a positional parameter: :type:value. Type
      may be omitted to indicate a string: name::value, or ::value.

  Returns:
    A list of query parameters in the form for the BigQuery API client.
  """
  if not parameters:
    return None
  results = []
  for param_string in parameters:
    if os.path.isfile(param_string):
      with open(param_string) as f:
        results += json.load(f)
    else:
      results.append(ParseParameter(param_string))
  return results


def SplitParam(param_string):
  split = param_string.split(':', 1)
  if len(split) != 2:
    raise app.UsageError(
        'Query parameters must be of the form: '
        '"name:type:value", ":type:value", or "name::value". '
        'An empty name produces a positional parameter. '
        'An empty type produces a STRING parameter.'
    )
  return split


def ParseParameter(param_string):
  """Parse a string of the form <name><type>:<value> into each part."""
  name, param_string = SplitParam(param_string)
  try:
    type_dict, value_dict = ParseParameterTypeAndValue(param_string)
  except app.UsageError as e:
    print('Error parsing parameter %s: %s' % (name, e))
    sys.exit(1)
  result = {'parameterType': type_dict, 'parameterValue': value_dict}
  if name:
    result['name'] = name
  return result


def ParseParameterTypeAndValue(param_string):
  """Parse a string of the form <recursive_type>:<value> into each part."""
  type_string, value_string = SplitParam(param_string)
  if not type_string:
    type_string = 'STRING'
  type_dict = ParseParameterType(type_string)
  return type_dict, ParseParameterValue(type_dict, value_string)


def ParseParameterType(type_string):
  """Parse a parameter type string into a JSON dict for the BigQuery API."""
  type_dict = {'type': type_string.upper()}
  if type_string.upper().startswith('ARRAY<') and type_string.endswith('>'):
    type_dict = {
        'type': 'ARRAY',
        'arrayType': ParseParameterType(type_string[6:-1]),
    }
  if type_string.startswith('STRUCT<') and type_string.endswith('>'):
    type_dict = {
        'type': 'STRUCT',
        'structTypes': ParseStructType(type_string[7:-1]),
    }
  if type_string.startswith('RANGE<') and type_string.endswith('>'):
    type_dict = {
        'type': 'RANGE',
        'rangeElementType': ParseParameterType(type_string[6:-1]),
    }
  if not type_string:
    raise app.UsageError('Query parameter missing type')
  return type_dict


def ParseStructType(type_string):
  """Parse a Struct QueryParameter type into a JSON dict form."""
  subtypes = []
  for name, sub_type in StructTypeSplit(type_string):
    subtypes.append({'type': ParseParameterType(sub_type), 'name': name})
  return subtypes


def StructTypeSplit(type_string):
  """Yields single field-name, sub-types tuple from a StructType string.

  Raises:
    UsageError: When a field name is missing.
  """
  while type_string:
    next_span = type_string.split(',', 1)[0]
    if '<' in next_span:
      angle_count = 0
      i = 0
      for i in range(next_span.find('<'), len(type_string)):
        if type_string[i] == '<':
          angle_count += 1
        if type_string[i] == '>':
          angle_count -= 1
        if angle_count == 0:
          break
      if angle_count != 0:
        raise app.UsageError('Malformatted struct type')
      next_span = type_string[: i + 1]
    type_string = type_string[len(next_span) + 1 :]
    splits = next_span.split(None, 1)
    if len(splits) != 2:
      raise app.UsageError('Struct parameter missing name for field')
    yield splits


def FormatRfc3339(datetime_obj: datetime.datetime) -> str:
  """Formats a datetime.datetime object (UTC) in RFC3339.

  https://developers.google.com/protocol-buffers/docs/reference/google.protobuf#timestamp

  Args:
    datetime_obj: A datetime.datetime object representing a datetime in UTC.

  Returns:
    The string representation of the date in RFC3339.
  """
  return datetime_obj.isoformat('T') + 'Z'


def ParseRangeParameterValue(range_value: str) -> Tuple[str, str]:
  """Parse a range parameter value string into its components.

  Args:
    range_value: A range value string of the form "[<start>, <end>)".

  Returns:
    A tuple (<start>, <end>).

  Raises:
    app.UsageError: if the input range value string was not formatted correctly.
  """
  parsed = ParseRangeString(range_value)
  if parsed is None:
    raise app.UsageError(
        f'Invalid range parameter value: {range_value}. Expected format:'
        ' "[<start>, <end>)"'
    )
  return parsed


def ParseParameterValue(type_dict, value_input):
  """Parse a parameter value of type `type_dict` from value_input.

  Arguments:
    type_dict: The JSON-dict type as which to parse `value_input`.
    value_input: Either a string representing the value, or a JSON dict for
      array and value types.
  """
  if 'structTypes' in type_dict:
    if isinstance(value_input, str):
      if value_input == 'NULL':
        return {'structValues': None}
      value_input = json.loads(value_input)
    type_map = dict([(x['name'], x['type']) for x in type_dict['structTypes']])
    values = {}
    for field_name, value in value_input.items():
      values[field_name] = ParseParameterValue(type_map[field_name], value)
    return {'structValues': values}
  if 'arrayType' in type_dict:
    if isinstance(value_input, str):
      if value_input == 'NULL':
        return {'arrayValues': None}
      try:
        value_input = json.loads(value_input)
      except json.decoder.JSONDecodeError:
        tb = sys.exc_info()[2]
        # pylint: disable=raise-missing-from
        raise app.UsageError(
            'Error parsing string as JSON: %s' % value_input
        ).with_traceback(tb)
    values = [
        ParseParameterValue(type_dict['arrayType'], x) for x in value_input
    ]
    if not values:  # Workaround to pass empty array parameter.
      return {'value': {}}  # An empty arrayValues list is the same as NULL.
    return {'arrayValues': values}
  if 'rangeElementType' in type_dict:
    if value_input == 'NULL':
      return {'rangeValue': None}
    start, end = ParseRangeParameterValue(value_input)
    return {
        'rangeValue': {
            'start': ParseParameterValue(type_dict['rangeElementType'], start),
            'end': ParseParameterValue(type_dict['rangeElementType'], end),
        }
    }
  return {'value': value_input if value_input != 'NULL' else None}
