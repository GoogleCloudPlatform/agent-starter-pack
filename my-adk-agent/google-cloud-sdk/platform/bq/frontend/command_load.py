#!/usr/bin/env python
"""All the BigQuery CLI commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import time
from typing import Optional

from absl import flags

import bq_flags
from clients import client_job
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import flags as frontend_flags
from frontend import utils as frontend_utils
from frontend import utils_flags
from frontend import utils_formatting

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Load(bigquery_command.BigqueryCmd):
  usage = """load <destination_table> <source> <schema>"""
  command = 'load'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Load, self).__init__(name, fv)
    flags.DEFINE_string(
        'field_delimiter',
        None,
        'The character that indicates the boundary between columns in the '
        'input file. "\\t" and "tab" are accepted names for tab.',
        short_name='F',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'encoding',
        None,
        ['UTF-8', 'ISO-8859-1', 'UTF-16BE', 'UTF-16LE', 'UTF-32BE', 'UTF-32LE'],
        (
            'The character encoding used by the input file.  Options include:'
            '\n ISO-8859-1 (also known as Latin-1)'
            '\n UTF-8'
            '\n UTF-16BE (UTF-16 BigEndian)'
            '\n UTF-16LE (UTF-16 LittleEndian)'
            '\n UTF-32BE (UTF-32 BigEndian)'
            '\n UTF-32LE (UTF-32 LittleEndian)'
        ),
        short_name='E',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'skip_leading_rows',
        None,
        'The number of rows at the beginning of the source file to skip.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'schema',
        None,
        'Either a filename or a comma-separated list of fields in the form '
        'name[:type].',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'replace',
        False,
        'If true existing data is erased when new data is loaded.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'replace_data',
        False,
        'If true, erase existing contents but not other table metadata like'
        ' schema before loading new data.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'quote',
        None,
        'Quote character to use to enclose records. Default is ". '
        'To indicate no quote character at all, use an empty string.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_bad_records',
        None,
        'Maximum number of bad records allowed before the entire job fails. '
        'Only supported for CSV and NEWLINE_DELIMITED_JSON file formats.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'allow_quoted_newlines',
        None,
        'Whether to allow quoted newlines in CSV import data.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'allow_jagged_rows',
        None,
        'Whether to allow missing trailing optional columns '
        'in CSV import data.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'preserve_ascii_control_characters',
        None,
        'Whether to preserve embedded Ascii Control characters in CSV import '
        'data.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'ignore_unknown_values',
        None,
        'Whether to allow and ignore extra, unrecognized values in CSV or JSON '
        'import data.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'source_format',
        None,
        [
            'CSV',
            'NEWLINE_DELIMITED_JSON',
            'DATASTORE_BACKUP',
            'AVRO',
            'PARQUET',
            'ORC',
            'THRIFT',
        ],
        'Format of source data. Options include:'
        '\n CSV'
        '\n NEWLINE_DELIMITED_JSON'
        '\n DATASTORE_BACKUP'
        '\n AVRO'
        '\n PARQUET'
        '\n ORC'
        '\n THRIFT',
        flag_values=fv,
    )
    flags.DEFINE_list(
        'projection_fields',
        [],
        'If sourceFormat is set to "DATASTORE_BACKUP", indicates which entity '
        'properties to load into BigQuery from a Cloud Datastore backup. '
        'Property names are case sensitive and must refer to top-level '
        'properties.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'autodetect',
        None,
        'Enable auto detection of schema and options for formats that are not '
        'self describing like CSV and JSON.',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'schema_update_option',
        None,
        'Can be specified when append to a table, or replace a table partition.'
        ' When specified, the schema of the destination table will be updated '
        'with the schema of the new data. One or more of the following options '
        'can be specified:'
        '\n ALLOW_FIELD_ADDITION: allow new fields to be added'
        '\n ALLOW_FIELD_RELAXATION: allow relaxing required fields to nullable',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'null_marker',
        None,
        'An optional custom string that will represent a NULL value'
        'in CSV import data.',
        flag_values=fv,
    )
    flags.DEFINE_list(
        'null_markers',
        [],
        'An optional list of custom strings that will represent a NULL value'
        'in CSV import data.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'time_partitioning_type',
        None,
        'Enables time based partitioning on the table and set the type. The '
        'default value is DAY, which will generate one partition per day. '
        'Other supported values are HOUR, MONTH, and YEAR.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'time_partitioning_expiration',
        None,
        'Enables time based partitioning on the table and sets the number of '
        'seconds for which to keep the storage for the partitions in the table.'
        ' The storage in a partition will have an expiration time of its '
        'partition time plus this value.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'range_partitioning',
        None,
        'Enables range partitioning on the table. The format should be '
        '"field,start,end,interval". The table will be partitioned based on the'
        ' value of the field. Field must be a top-level, non-repeated INT64 '
        'field. Start, end, and interval are INT64 values defining the ranges.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'time_partitioning_field',
        None,
        'Enables time based partitioning on the table and the table will be '
        'partitioned based on the value of this field. If time based '
        'partitioning is enabled without this value, the table will be '
        'partitioned based on the loading time.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'destination_kms_key',
        None,
        'Cloud KMS key for encryption of the destination table data.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'require_partition_filter',
        None,
        'Whether to require partition filter for queries over this table. '
        'Only apply to partitioned table.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'clustering_fields',
        None,
        'Comma-separated list of field names that specifies the columns on '
        'which a table is clustered. To remove the clustering, set an empty '
        'value.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_avro_logical_types',
        None,
        'If sourceFormat is set to "AVRO", indicates whether to enable '
        'interpreting logical types into their corresponding types '
        '(ie. TIMESTAMP), instead of only using their raw types (ie. INTEGER).',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'reference_file_schema_uri',
        None,
        'provide a reference file with the reader schema, currently '
        'enabled for the format: AVRO, PARQUET, ORC.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'parquet_enum_as_string',
        None,
        'Infer Parquet ENUM logical type as STRING '
        '(instead of BYTES by default).',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'parquet_enable_list_inference',
        None,
        frontend_utils.PARQUET_LIST_INFERENCE_DESCRIPTION,
        flag_values=fv,
    )
    flags.DEFINE_string(
        'hive_partitioning_mode',
        None,
        'Enables hive partitioning.  AUTO indicates to perform '
        'automatic type inference.  STRINGS indicates to treat all hive '
        'partition keys as STRING typed.  No other values are accepted',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'hive_partitioning_source_uri_prefix',
        None,
        'Prefix after which hive partition '
        'encoding begins.  For URIs like gs://bucket/path/key1=value/file, '
        'the value should be gs://bucket/path.',
        flag_values=fv,
    )
    flags.DEFINE_multi_enum(
        'decimal_target_types',
        None,
        ['NUMERIC', 'BIGNUMERIC', 'STRING'],
        'Specifies the list of possible BigQuery data types to '
        'which the source decimal values are converted. This list and the '
        'precision and the scale parameters of the decimal field determine the '
        'target type in the following preference order, and '
        'one or more of the following options could be specified: '
        '\n NUMERIC: decimal values could be converted to NUMERIC type, '
        'depending on the precision and scale of the decimal schema.'
        '\n BIGNUMERIC: decimal values could be converted to BIGNUMERIC type, '
        'depending on the precision and scale of the decimal schema.'
        '\n STRING: decimal values could be converted to STRING type, '
        'depending on the precision and scale of the decimal schema.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'file_set_spec_type',
        None,
        ['FILE_SYSTEM_MATCH', 'NEW_LINE_DELIMITED_MANIFEST'],
        'Specifies how to discover files given source URIs. '
        'Options include: '
        '\n FILE_SYSTEM_MATCH: expand source URIs by listing files from the '
        'underlying object store. This is the default behavior.'
        '\n NEW_LINE_DELIMITED_MANIFEST: indicate the source URIs provided are '
        'new line delimited manifest files, where each line contains a URI '
        'with no wild-card.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'thrift_schema_idl_root_dir',
        None,
        'If "source_format" is set to "THRIFT", indicates the root directory '
        'of the Thrift IDL bundle containing all Thrift files that should be '
        'used to parse the schema of the serialized Thrift records.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'thrift_schema_idl_uri',
        None,
        'If "source_format" is set to "THRIFT", indicates the file uri that '
        'contains the Thrift IDL struct to be parsed as schema. This file will '
        'be used as the entry point to parse the schema and all its included '
        'Thrift IDL files should be in "thrift_schema_idl_root_dir".',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'thrift_schema_struct',
        None,
        'If "source_format" is set to "THRIFT", indicates the root Thrift '
        'struct that should be used as the schema. This struct should be '
        'defined in the "thrift_schema_idl_uri" file.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'thrift_deserialization',
        None,
        ['T_BINARY_PROTOCOL'],
        'If "source_format" is set to "THRIFT", configures how serialized '
        'Thrift record should be deserialized (using TProtocol). '
        'Options include: '
        '\n T_BINARY_PROTOCOL',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'thrift_framing',
        None,
        ['NOT_FRAMED', 'FRAMED_WITH_BIG_ENDIAN', 'FRAMED_WITH_LITTLE_ENDIAN'],
        'If "source_format" is set to "THRIFT", configures how Thrift records '
        'or data blocks are framed (e.g. using TFramedTransport). '
        'Options includes: '
        '\n NOT_FRAMED, '
        '\n FRAMED_WITH_BIG_ENDIAN, '
        '\n FRAMED_WITH_LITTLE_ENDIAN',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'boundary_bytes_base64',
        None,
        'If "source_format" is set to "THRIFT", indicates the sequence of '
        'boundary bytes (encoded in base64) that are added in front of the '
        'serialized Thrift records, or data blocks, or the frame when used '
        'with `thrift_framing`.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'numeric_type_conversion_mode',
        None,
        ['ROUND'],
        'Allowed values: '
        'ROUND: round the numeric values if the value has higher precision in '
        'the fractional part than the supported scale of 9. Default behavior '
        '(i.e., missing of this property): the numbers with scale larger than '
        '9 will cause the load job to fail.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'json_extension',
        None,
        ['GEOJSON'],
        '(experimental) Allowed values: '
        'GEOJSON: only allowed when source_format is specified as '
        'NEWLINE_DELIMITED_JSON. When specified, the input is loaded as '
        'newline-delimited GeoJSON.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'column_name_character_map',
        None,
        ['STRICT', 'V1', 'V2'],
        'Indicates the character map used for column names: '
        '\n STRICT: The latest character map and reject invalid column names.'
        '\n V1: Supports alphanumeric + underscore and name must start with a '
        'letter or underscore. Invalid column names will be normalized.'
        '\n V2: Supports flexible column name. Invalid column names will be '
        'normalized.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'session_id',
        None,
        'If loading to a temporary table, specifies the session ID of the '
        'temporary table',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'copy_files_only',
        None,
        '[Experimental] Configures the load job to only copy files to the '
        'destination BigLake managed table, without reading file content and '
        'writing them to new files.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'time_zone',
        None,
        'Default time zone that will apply when parsing timestamp values that'
        ' have no specific time zone. For example, "America/Los_Angeles".',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'date_format',
        None,
        'Format elements that define how the DATE values are formatted in the'
        ' input files. For example, "MM/DD/YYYY".',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'datetime_format',
        None,
        'Format elements that define how the DATETIME values are formatted in'
        ' the input files. For example, "MM/DD/YYYY HH24:MI:SS.FF3".',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'time_format',
        None,
        'Format elements that define how the TIME values are formatted in the'
        ' input files. For example, "HH24:MI:SS.FF3".',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'timestamp_format',
        None,
        'Format elements that define how the TIMESTAMP values are formatted in'
        ' the input files. For example, "MM/DD/YYYY HH24:MI:SS.FF3".',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'source_column_match',
        None,
        ['POSITION', 'NAME'],
        'Controls the strategy used to match loaded columns to the schema.'
        ' Options include:'
        '\n POSITION: matches by position. This option assumes that the columns'
        ' are ordered the same way as the schema.'
        '\n NAME: matches by name. This option reads the header row as column'
        ' names and reorders columns to match the field names in the schema.',
        flag_values=fv,
    )
    self.timestamp_target_precision_flag = (
        frontend_flags.define_timestamp_target_precision(flag_values=fv)
    )
    self.parquet_map_target_type_flag = (
        frontend_flags.define_parquet_map_target_type(flag_values=fv)
    )
    self.reservation_id_for_a_job_flag = (
        frontend_flags.define_reservation_id_for_a_job(flag_values=fv)
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(
      self, destination_table: str, source: str, schema: Optional[str] = None
  ) -> Optional[int]:
    """Perform a load operation of source into destination_table.

    Usage:
      load <destination_table> <source> [<schema>] [--session_id=[session]]

    The <destination_table> is the fully-qualified table name of table to
    create, or append to if the table already exists.

    To load to a temporary table, specify the table name in <destination_table>
    without a dataset and specify the session id with --session_id.

    The <source> argument can be a path to a single local file, or a
    comma-separated list of URIs.

    The <schema> argument should be either the name of a JSON file or a text
    schema. This schema should be omitted if the table already has one.

    In the case that the schema is provided in text form, it should be a
    comma-separated list of entries of the form name[:type], where type will
    default to string if not specified.

    In the case that <schema> is a filename, it should be a JSON file
    containing a single array, each entry of which should be an object with
    properties 'name', 'type', and (optionally) 'mode'. For more detail:
    https://cloud.google.com/bigquery/docs/schemas#specifying_a_json_schema_file

    Note: the case of a single-entry schema with no type specified is
    ambiguous; one can use name:string to force interpretation as a
    text schema.

    Examples:
      bq load ds.new_tbl ./info.csv ./info_schema.json
      bq load ds.new_tbl gs://mybucket/info.csv ./info_schema.json
      bq load ds.small gs://mybucket/small.csv name:integer,value:string
      bq load ds.small gs://mybucket/small.csv field1,field2,field3
      bq load temp_tbl --session_id=my_session ./info.csv ./info_schema.json

    Arguments:
      destination_table: Destination table name.
      source: Name of local file to import, or a comma-separated list of URI
        paths to data to import.
      schema: Either a text schema or JSON file, as above.
    """
    client = bq_cached_client.Client.Get()
    default_dataset_id = ''
    if self.session_id:
      default_dataset_id = '_SESSION'
    table_reference = bq_client_utils.GetTableReference(
        id_fallbacks=client,
        identifier=destination_table,
        default_dataset_id=default_dataset_id,
    )
    opts = {
        'encoding': self.encoding,
        'skip_leading_rows': self.skip_leading_rows,
        'allow_quoted_newlines': self.allow_quoted_newlines,
        'job_id': utils_flags.get_job_id_from_flags(),
        'source_format': self.source_format,
        'projection_fields': self.projection_fields,
    }
    if self.max_bad_records:
      opts['max_bad_records'] = self.max_bad_records
    if bq_flags.LOCATION.value:
      opts['location'] = bq_flags.LOCATION.value
    if self.session_id:
      opts['connection_properties'] = [
          {'key': 'session_id', 'value': self.session_id}
      ]
    if self.copy_files_only:
      opts['copy_files_only'] = self.copy_files_only
    if self.replace:
      opts['write_disposition'] = 'WRITE_TRUNCATE'
    elif self.replace_data:
      opts['write_disposition'] = 'WRITE_TRUNCATE_DATA'
    if self.field_delimiter is not None:
      opts['field_delimiter'] = frontend_utils.NormalizeFieldDelimiter(
          self.field_delimiter
      )
    if self.quote is not None:
      opts['quote'] = frontend_utils.NormalizeFieldDelimiter(self.quote)
    if self.allow_jagged_rows is not None:
      opts['allow_jagged_rows'] = self.allow_jagged_rows
    if self.preserve_ascii_control_characters is not None:
      opts['preserve_ascii_control_characters'] = (
          self.preserve_ascii_control_characters
      )
    if self.ignore_unknown_values is not None:
      opts['ignore_unknown_values'] = self.ignore_unknown_values
    if self.autodetect is not None:
      opts['autodetect'] = self.autodetect
    if self.schema_update_option:
      opts['schema_update_options'] = self.schema_update_option
    if self.null_marker:
      opts['null_marker'] = self.null_marker
    if self.null_markers is not None:
      opts['null_markers'] = self.null_markers
    time_partitioning = frontend_utils.ParseTimePartitioning(
        self.time_partitioning_type,
        self.time_partitioning_expiration,
        self.time_partitioning_field,
        None,
        self.require_partition_filter,
    )
    if time_partitioning is not None:
      opts['time_partitioning'] = time_partitioning
    range_partitioning = frontend_utils.ParseRangePartitioning(
        self.range_partitioning
    )
    if range_partitioning:
      opts['range_partitioning'] = range_partitioning
    clustering = frontend_utils.ParseClustering(self.clustering_fields)
    if clustering:
      opts['clustering'] = clustering
    if self.destination_kms_key is not None:
      opts['destination_encryption_configuration'] = {
          'kmsKeyName': self.destination_kms_key
      }
    if self.use_avro_logical_types is not None:
      opts['use_avro_logical_types'] = self.use_avro_logical_types
    if self.reference_file_schema_uri is not None:
      opts['reference_file_schema_uri'] = self.reference_file_schema_uri
    if self.hive_partitioning_mode is not None:
      frontend_utils.ValidateHivePartitioningOptions(
          self.hive_partitioning_mode
      )
      hive_partitioning_options = {}
      hive_partitioning_options['mode'] = self.hive_partitioning_mode
      if self.hive_partitioning_source_uri_prefix is not None:
        hive_partitioning_options['sourceUriPrefix'] = (
            self.hive_partitioning_source_uri_prefix
        )
      opts['hive_partitioning_options'] = hive_partitioning_options
    if self.numeric_type_conversion_mode:
      opts['numeric_type_conversion_mode'] = (
          frontend_utils.ParseNumericTypeConversionMode(
              self.numeric_type_conversion_mode
          )
      )
    if self.json_extension is not None:
      opts['json_extension'] = self.json_extension
    if self.column_name_character_map is not None:
      opts['column_name_character_map'] = self.column_name_character_map
    opts['decimal_target_types'] = self.decimal_target_types
    if self.file_set_spec_type is not None:
      opts['file_set_spec_type'] = frontend_utils.ParseFileSetSpecType(
          self.file_set_spec_type
      )
    if self.time_zone is not None:
      opts['time_zone'] = self.time_zone
    if self.date_format is not None:
      opts['date_format'] = self.date_format
    if self.datetime_format is not None:
      opts['datetime_format'] = self.datetime_format
    if self.time_format is not None:
      opts['time_format'] = self.time_format
    if self.timestamp_format is not None:
      opts['timestamp_format'] = self.timestamp_format
    if self.source_column_match is not None:
      opts['source_column_match'] = self.source_column_match
    if self.timestamp_target_precision_flag.value is not None:
      opts['timestamp_target_precision'] = (
          self.timestamp_target_precision_flag.value
      )
    if opts['source_format'] == 'THRIFT':
      thrift_options = {}
      if self.thrift_schema_idl_root_dir is not None:
        thrift_options['schema_idl_root_dir'] = self.thrift_schema_idl_root_dir
      if self.thrift_schema_idl_uri is not None:
        thrift_options['schema_idl_uri'] = self.thrift_schema_idl_uri
      if self.thrift_schema_struct is not None:
        thrift_options['schema_struct'] = self.thrift_schema_struct
      # Default to 'THRIFT_BINARY_PROTOCOL_OPTION'.
      thrift_options['deserialization_option'] = 'THRIFT_BINARY_PROTOCOL_OPTION'
      if self.thrift_deserialization is not None:
        if self.thrift_deserialization == 'T_BINARY_PROTOCOL':
          thrift_options['deserialization_option'] = (
              'THRIFT_BINARY_PROTOCOL_OPTION'
          )
      # Default to 'NOT_FRAMED'.
      thrift_options['framing_option'] = 'NOT_FRAMED'
      if self.thrift_framing is not None:
        thrift_options['framing_option'] = self.thrift_framing
      if self.boundary_bytes_base64 is not None:
        thrift_options['boundary_bytes'] = self.boundary_bytes_base64
      opts['thrift_options'] = thrift_options
    if opts['source_format'] == 'PARQUET':
      parquet_options = {}
      if self.parquet_enum_as_string is not None:
        parquet_options['enum_as_string'] = self.parquet_enum_as_string
      if self.parquet_enable_list_inference is not None:
        parquet_options['enable_list_inference'] = (
            self.parquet_enable_list_inference
        )
      if self.parquet_map_target_type_flag.value is not None:
        parquet_options['mapTargetType'] = (
            self.parquet_map_target_type_flag.value
        )
      if parquet_options:
        opts['parquet_options'] = parquet_options
    if self.reservation_id_for_a_job_flag.present:
      opts['reservation_id'] = self.reservation_id_for_a_job_flag.value
    job = client_job.Load(
        client, table_reference, source, schema=schema, **opts
    )
    if bq_flags.SYNCHRONOUS_MODE.value:
      frontend_utils.PrintJobMessages(utils_formatting.format_job_info(job))
    else:
      self.PrintJobStartInfo(job)
