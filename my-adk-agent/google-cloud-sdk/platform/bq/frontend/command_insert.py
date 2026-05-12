#!/usr/bin/env python
"""The BQ CLI `insert` command."""

import sys
from typing import Optional, TextIO

from absl import app
from absl import flags

import bq_flags
import bq_utils
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils
from pyglib import stringutil

FLAGS = flags.FLAGS

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Insert(bigquery_command.BigqueryCmd):
  usage = """insert [-s] [-i] [-x=<suffix>] <table identifier> [file]"""
  command = 'insert'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Insert, self).__init__(name, fv)
    flags.DEFINE_boolean(
        'skip_invalid_rows',
        None,
        'Attempt to insert any valid rows, even if invalid rows are present.',
        short_name='s',
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
        'template_suffix',
        None,
        'If specified, treats the destination table as a base template, and '
        'inserts the rows into an instance table named '
        '"{destination}{templateSuffix}". BigQuery will manage creation of the '
        'instance table, using the schema of the base template table.',
        short_name='x',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'insert_id',
        None,
        'Used to ensure repeat executions do not add unintended data. '
        'A present insert_id value will be appended to the row number of '
        'each row to be inserted and used as the insertId field for the row. '
        'Internally the insertId field is used for deduping of inserted rows.',
        flag_values=fv,
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(
      self, identifier: str = '', filename: Optional[str] = None
  ) -> Optional[int]:
    """Inserts rows in a table.

    Inserts the records formatted as newline delimited JSON from file
    into the specified table. If file is not specified, reads from stdin.
    If there were any insert errors it prints the errors to stdout.

    Examples:
      bq insert dataset.table /tmp/mydata.json
      echo '{"a":1, "b":2}' | bq insert dataset.table

    Template table examples:
    Insert to dataset.table_suffix table using dataset.table table as its
    template.
      bq insert -x=_suffix dataset.table /tmp/mydata.json
    """
    if filename:
      with open(filename, 'r') as json_file:
        return self._DoInsert(
            identifier,
            json_file,
            skip_invalid_rows=self.skip_invalid_rows,
            ignore_unknown_values=self.ignore_unknown_values,
            template_suffix=self.template_suffix,
            insert_id=self.insert_id,
        )
    else:
      return self._DoInsert(
          identifier,
          sys.stdin,
          skip_invalid_rows=self.skip_invalid_rows,
          ignore_unknown_values=self.ignore_unknown_values,
          template_suffix=self.template_suffix,
          insert_id=self.insert_id,
      )

  def _DoInsert(
      self,
      identifier: str,
      json_file: TextIO,
      skip_invalid_rows: Optional[bool] = None,
      ignore_unknown_values: Optional[bool] = None,
      template_suffix: Optional[int] = None,
      insert_id: Optional[str] = None,
  ) -> int:
    """Insert the contents of the file into a table."""
    client = bq_cached_client.Client.Get()
    reference = bq_client_utils.GetReference(
        id_fallbacks=client, identifier=identifier
    )
    bq_id_utils.typecheck(
        reference,
        (bq_id_utils.ApiClientHelper.TableReference,),
        'Must provide a table identifier for insert.',
        is_usage_error=True,
    )
    batch = []

    def Flush():
      result = client_table.insert_table_rows(
          insert_client=client.GetInsertApiClient(),
          table_dict=reference,
          inserts=batch,
          skip_invalid_rows=skip_invalid_rows,
          ignore_unknown_values=ignore_unknown_values,
          template_suffix=template_suffix,
      )
      del batch[:]
      return result, result.get('insertErrors', None)

    result = {}
    errors = None
    lineno = 1
    for line in json_file:
      try:
        unique_insert_id = None
        if insert_id is not None:
          unique_insert_id = insert_id + '_' + str(lineno)
        batch.append(
            bq_processor_utils.JsonToInsertEntry(unique_insert_id, line)
        )
        lineno += 1
      except bq_error.BigqueryClientError as e:
        raise app.UsageError('Line %d: %s' % (lineno, str(e)))
      if (
          FLAGS.max_rows_per_request
          and len(batch) == FLAGS.max_rows_per_request
      ):
        result, errors = Flush()
      if errors:
        break
    if batch and not errors:
      result, errors = Flush()

    if bq_flags.FORMAT.value in ['prettyjson', 'json']:
      bq_utils.PrintFormattedJsonObject(result)
    elif bq_flags.FORMAT.value in [None, 'sparse', 'pretty']:
      if errors:
        for entry in result['insertErrors']:
          entry_errors = entry['errors']
          sys.stdout.write('record %d errors: ' % (entry['index'],))
          for error in entry_errors:
            print(
                '\t%s: %s'
                % (
                    stringutil.ensure_str(error['reason']),
                    stringutil.ensure_str(error.get('message')),
                )
            )
    return 1 if errors else 0
