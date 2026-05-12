#!/usr/bin/env python
"""The BigQuery CLI extract command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

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


class Extract(bigquery_command.BigqueryCmd):
  usage = """extract <source_table> <destination_uris>"""
  command = 'extract'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Extract, self).__init__(name, fv)
    flags.DEFINE_string(
        'field_delimiter',
        None,
        'The character that indicates the boundary between columns in the '
        'output file. "\\t" and "tab" are accepted names for tab. '
        'Not applicable when extracting models.',
        short_name='F',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'destination_format',
        None,
        [
            'CSV',
            'NEWLINE_DELIMITED_JSON',
            'AVRO',
            'PARQUET',
            'ML_TF_SAVED_MODEL',
            'ML_XGBOOST_BOOSTER',
        ],
        'The extracted file format. Format CSV, NEWLINE_DELIMITED_JSON, '
        'PARQUET and AVRO are applicable for extracting tables. '
        'Formats ML_TF_SAVED_MODEL and ML_XGBOOST_BOOSTER are applicable for '
        'extracting models. The default value for tables is CSV. Tables with '
        'nested or repeated fields cannot be exported as CSV. The default '
        'value for models is ML_TF_SAVED_MODEL.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'trial_id',
        None,
        '1-based ID of the trial to be exported from a hyperparameter tuning '
        'model. The default_trial_id will be exported if not specified. This '
        'does not apply for models not trained with hyperparameter tuning.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'add_serving_default_signature',
        None,
        'Whether to add serving_default signature for export BigQuery ML '
        'trained tf based models.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'compression',
        'NONE',
        ['GZIP', 'DEFLATE', 'SNAPPY', 'ZSTD', 'NONE'],
        'The compression type to use for exported files. Possible values '
        'include GZIP, DEFLATE, SNAPPY, ZSTD, and NONE. The default value is '
        'None. Not applicable when extracting models.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'print_header',
        None,
        'Whether to print header rows for formats that '
        'have headers. Prints headers by default.'
        'Not applicable when extracting models.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_avro_logical_types',
        None,
        'If destinationFormat is set to "AVRO", this flag indicates whether to '
        'enable extracting applicable column types (such as TIMESTAMP) to '
        'their corresponding AVRO logical types (timestamp-micros), instead of '
        'only using their raw types (avro-long). '
        'Not applicable when extracting models.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'model',
        False,
        'Extract model with this model ID.',
        short_name='m',
        flag_values=fv,
    )
    self.reservation_id_for_a_job_flag = (
        frontend_flags.define_reservation_id_for_a_job(flag_values=fv)
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(
      self, identifier: str, destination_uris: str
  ) -> Optional[int]:
    """Perform an extract operation of source into destination_uris.

    Usage:
      extract <source_table> <destination_uris>

    Use -m option to extract a source_model.

    Examples:
      bq extract ds.table gs://mybucket/table.csv
      bq extract -m ds.model gs://mybucket/model

    Arguments:
      source_table: Source table to extract.
      source_model: Source model to extract.
      destination_uris: One or more Google Cloud Storage URIs, separated by
        commas.
    """
    client = bq_cached_client.Client.Get()
    kwds = {
        'job_id': utils_flags.get_job_id_from_flags(),
    }
    if bq_flags.LOCATION.value:
      kwds['location'] = bq_flags.LOCATION.value
    if self.reservation_id_for_a_job_flag.present:
      kwds['reservation_id'] = self.reservation_id_for_a_job_flag.value

    if self.m:
      reference = bq_client_utils.GetModelReference(
          id_fallbacks=client, identifier=identifier
      )
    else:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
    job = client_job.Extract(
        client,
        reference,
        destination_uris,
        print_header=self.print_header,
        field_delimiter=frontend_utils.NormalizeFieldDelimiter(
            self.field_delimiter
        ),
        destination_format=self.destination_format,
        trial_id=self.trial_id,
        add_serving_default_signature=self.add_serving_default_signature,
        compression=self.compression,
        use_avro_logical_types=self.use_avro_logical_types,
        **kwds,
    )
    if bq_flags.SYNCHRONOUS_MODE.value:
      # If we are here, the job succeeded, but print warnings if any.
      frontend_utils.PrintJobMessages(utils_formatting.format_job_info(job))
    else:
      self.PrintJobStartInfo(job)
