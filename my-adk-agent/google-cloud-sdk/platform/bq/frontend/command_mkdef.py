#!/usr/bin/env python
"""The BigQuery CLI mkdef command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import sys
from typing import Optional

from absl import flags

from frontend import bigquery_command
from frontend import flags as frontend_flags
from frontend import utils as frontend_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class MakeExternalTableDefinition(bigquery_command.BigqueryCmd):
  usage = """mkdef <source_uri> [<schema>]"""
  command = 'mkdef'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(MakeExternalTableDefinition, self).__init__(name, fv)

    flags.DEFINE_boolean(
        'autodetect',
        None,
        'Should schema and format options be autodetected.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'ignore_unknown_values',
        None,
        'Ignore any values in a row that are not present in the schema.',
        short_name='i',
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
    flags.DEFINE_boolean(
        'require_hive_partition_filter',
        None,
        'Whether queries against a table are required to '
        'include a hive partition key in a query predicate.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'source_format',
        'CSV',
        [
            'CSV',
            'GOOGLE_SHEETS',
            'NEWLINE_DELIMITED_JSON',
            'DATASTORE_BACKUP',
            'DELTA_LAKE',
            'ORC',
            'PARQUET',
            'AVRO',
            'ICEBERG',
        ],
        'Format of source data. Options include:'
        '\n CSV'
        '\n GOOGLE_SHEETS'
        '\n NEWLINE_DELIMITED_JSON'
        '\n DATASTORE_BACKUP'
        '\n DELTA_LAKE'
        '\n ORC'
        '\n PARQUET'
        '\n ICEBERG'
        '\n AVRO',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'connection_id',
        None,
        'The connection specifying the credentials to be used to read external '
        'storage, such as Azure Blob, Cloud Storage, or S3. The connection_id '
        'can have the form "<project_id>.<location_id>.<connection_id>" or '
        '"projects/<project_id>/locations/<location_id>/connections/'
        '<connection_id>".',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_avro_logical_types',
        True,
        'If sourceFormat is set to "AVRO", indicates whether to enable '
        'interpreting logical types into their corresponding types '
        '(ie. TIMESTAMP), instead of only using their raw types (ie. INTEGER).',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'parquet_enum_as_string',
        False,
        'Infer Parquet ENUM logical type as STRING '
        '(instead of BYTES by default).',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'parquet_enable_list_inference',
        False,
        frontend_utils.PARQUET_LIST_INFERENCE_DESCRIPTION,
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'metadata_cache_mode',
        None,
        ['AUTOMATIC', 'MANUAL'],
        'Enables metadata cache for an external table with a connection. '
        'Specify AUTOMATIC to automatically refresh the cached metadata. '
        'Specify MANUAL to stop the automatic refresh.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'object_metadata',
        None,
        ['DIRECTORY', 'SIMPLE'],
        'Object Metadata Type. Options include:\n SIMPLE.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'preserve_ascii_control_characters',
        False,
        'Whether to preserve embedded Ascii Control characters in CSV External '
        'table ',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'reference_file_schema_uri',
        None,
        'provide a referencing file with the expected table schema, currently '
        'enabled for the formats: AVRO, PARQUET, ORC.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'encoding',
        None,
        ['UTF-8', 'ISO-8859-1', 'UTF-16BE', 'UTF-16LE', 'UTF-32BE', 'UTF-32LE'],
        'The character encoding used by the input file.  Options include:'
        '\n ISO-8859-1 (also known as Latin-1)'
        '\n UTF-8'
        '\n UTF-16BE (UTF-16 BigEndian)'
        '\n UTF-16LE (UTF-16 LittleEndian)'
        '\n UTF-32BE (UTF-32 BigEndian)'
        '\n UTF-32LE (UTF-16 LittleEndian)',
        short_name='E',
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
    self.null_marker_flag = frontend_flags.define_null_marker(flag_values=fv)
    self.null_markers_flag = frontend_flags.define_null_markers(flag_values=fv)
    self.time_zone_flag = frontend_flags.define_time_zone(flag_values=fv)
    self.date_format_flag = frontend_flags.define_date_format(flag_values=fv)
    self.datetime_format_flag = frontend_flags.define_datetime_format(
        flag_values=fv
    )
    self.time_format_flag = frontend_flags.define_time_format(flag_values=fv)
    self.timestamp_format_flag = frontend_flags.define_timestamp_format(
        flag_values=fv
    )
    self.source_column_match_flag = frontend_flags.define_source_column_match(
        flag_values=fv
    )
    self.parquet_map_target_type_flag = (
        frontend_flags.define_parquet_map_target_type(flag_values=fv)
    )
    self.timestamp_target_precision_flag = (
        frontend_flags.define_timestamp_target_precision(flag_values=fv)
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(
      self, source_uris: str, schema: Optional[str] = None
  ) -> Optional[int]:
    """Emits a definition in JSON for an external table, such as GCS.

    The output of this command can be redirected to a file and used for the
    external_table_definition flag with the "bq query" and "bq mk" commands.
    It produces a definition with the most commonly used values for options.
    You can modify the output to override option values.

    The <source_uris> argument is a comma-separated list of URIs indicating
    the data referenced by this external table.

    The <schema> argument should be either the name of a JSON file or a text
    schema.

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

    Usage:
      mkdef <source_uris> [<schema>]

    Examples:
      bq mkdef 'gs://bucket/file.csv' field1:integer,field2:string

    Arguments:
      source_uris: Comma-separated list of URIs.
      schema: Either a text schema or JSON file, as above.
    """
    # pylint: disable=line-too-long
    json.dump(
        frontend_utils.CreateExternalTableDefinition(
            source_format=self.source_format,
            source_uris=source_uris,
            schema=schema,
            autodetect=self.autodetect,
            connection_id=self.connection_id,
            ignore_unknown_values=self.ignore_unknown_values,
            hive_partitioning_mode=self.hive_partitioning_mode,
            hive_partitioning_source_uri_prefix=self.hive_partitioning_source_uri_prefix,
            require_hive_partition_filter=self.require_hive_partition_filter,
            use_avro_logical_types=self.use_avro_logical_types,
            parquet_enum_as_string=self.parquet_enum_as_string,
            parquet_enable_list_inference=self.parquet_enable_list_inference,
            metadata_cache_mode=self.metadata_cache_mode,
            object_metadata=self.object_metadata,
            preserve_ascii_control_characters=self.preserve_ascii_control_characters,
            reference_file_schema_uri=self.reference_file_schema_uri,
            encoding=self.encoding,
            file_set_spec_type=self.file_set_spec_type,
            null_marker=self.null_marker_flag.value,
            null_markers=self.null_markers_flag.value,
            time_zone=self.time_zone_flag.value,
            date_format=self.date_format_flag.value,
            datetime_format=self.datetime_format_flag.value,
            time_format=self.time_format_flag.value,
            timestamp_format=self.timestamp_format_flag.value,
            source_column_match=self.source_column_match_flag.value,
            parquet_map_target_type=self.parquet_map_target_type_flag.value,
            timestamp_target_precision=self.timestamp_target_precision_flag.value,
        ),
        sys.stdout,
        sort_keys=True,
        indent=2,
    )
    # pylint: enable=line-too-long
