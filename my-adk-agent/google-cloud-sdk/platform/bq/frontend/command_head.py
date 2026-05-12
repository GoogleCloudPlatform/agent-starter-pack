#!/usr/bin/env python
"""The BigQuery CLI head command."""

from typing import Optional

from absl import app
from absl import flags

import bq_flags
from clients import client_job
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import flags as frontend_flags
from utils import bq_id_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Head(bigquery_command.BigqueryCmd):
  usage = """head [-n <max rows>] [-j] [-t] <identifier>"""
  command = 'head'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Head, self).__init__(name, fv)
    flags.DEFINE_boolean(
        'job',
        False,
        'Reads the results of a query job.',
        short_name='j',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'table',
        False,
        'Reads rows from a table.',
        short_name='t',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'start_row',
        0,
        'The number of rows to skip before showing table data.',
        short_name='s',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_rows',
        100,
        'The number of rows to print when showing table data.',
        short_name='n',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'selected_fields',
        None,
        'A subset of fields (including nested fields) to return when showing '
        'table data. If not specified, full row will be retrieved. '
        'For example, "-c:a,b".',
        short_name='c',
        flag_values=fv,
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str = '') -> Optional[int]:
    # pylint: disable=g-doc-exception
    """Displays rows in a table.

    Examples:
      bq head dataset.table
      bq head -j job
      bq head -n 10 dataset.table
      bq head -s 5 -n 10 dataset.table
    """
    client = bq_cached_client.Client.Get()
    if self.j and self.t:
      raise app.UsageError('Cannot specify both -j and -t.')

    if self.j:
      reference = bq_client_utils.GetJobReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
      )
    else:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )

    use_full_timestamp = False

    if isinstance(reference, bq_id_utils.ApiClientHelper.JobReference):
      fields, rows = client_job.ReadSchemaAndJobRows(
          client,
          dict(reference),
          start_row=self.s,
          max_rows=self.n,
      )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
      fields, rows = client_table.read_schema_and_rows(
          apiclient=client.apiclient,
          table_ref=reference,
          start_row=self.s,
          max_rows=self.n,
          selected_fields=self.c,
          max_rows_per_request=client.max_rows_per_request,
      )
    else:
      raise app.UsageError("Invalid identifier '%s' for head." % (identifier,))

    bq_cached_client.Factory.ClientTablePrinter.GetTablePrinter().PrintTable(
        fields, rows, use_full_timestamp=use_full_timestamp
    )
