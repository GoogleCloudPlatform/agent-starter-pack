#!/usr/bin/env python
"""The different TableReader options for the BQ CLI."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import Optional

from googleapiclient import discovery

from utils import bq_error
from utils import bq_id_utils


class _TableReader:
  """Base class that defines the TableReader interface.

  _TableReaders provide a way to read paginated rows and schemas from a table.
  """

  def ReadRows(
      self,
      start_row: Optional[int] = 0,
      max_rows: Optional[int] = None,
      selected_fields: Optional[str] = None,
  ):
    """Read at most max_rows rows from a table.

    Args:
      start_row: first row to return.
      max_rows: maximum number of rows to return.
      selected_fields: a subset of fields to return.

    Raises:
      BigqueryInterfaceError: when bigquery returns something unexpected.

    Returns:
      list of rows, each of which is a list of field values.
    """
    (_, rows) = self.ReadSchemaAndRows(
        start_row=start_row,
        max_rows=max_rows,
        selected_fields=selected_fields,
    )
    return rows

  def ReadSchemaAndRows(
      self,
      start_row: Optional[int],
      max_rows: Optional[int],
      selected_fields: Optional[str] = None,
  ):
    """Read at most max_rows rows from a table and the schema.

    Args:
      start_row: first row to read.
      max_rows: maximum number of rows to return.
      selected_fields: a subset of fields to return.

    Raises:
      BigqueryInterfaceError: when bigquery returns something unexpected.
      ValueError: when start_row is None.
      ValueError: when max_rows is None.

    Returns:
      A tuple where the first item is the list of fields and the
      second item a list of rows.
    """
    if start_row is None:
      raise ValueError('start_row is required')
    if max_rows is None:
      raise ValueError('max_rows is required')
    page_token = None
    rows = []
    schema = {}
    while len(rows) < max_rows:
      rows_to_read = max_rows - len(rows)
      if not hasattr(self, 'max_rows_per_request'):
        raise NotImplementedError(
            'Subclass must have max_rows_per_request instance variable'
        )
      if self.max_rows_per_request:
        rows_to_read = min(self.max_rows_per_request, rows_to_read)
      (more_rows, page_token, current_schema) = self._ReadOnePage(
          None if page_token else start_row,
          max_rows=rows_to_read,
          page_token=page_token,
          selected_fields=selected_fields,
      )
      if not schema and current_schema:
        schema = current_schema.get('fields', [])
      for row in more_rows:
        rows.append(self._ConvertFromFV(schema, row))
        start_row += 1
      if not page_token or not more_rows:
        break
    return (schema, rows)

  def _ConvertFromFV(self, schema, row):
    """Converts from FV format to possibly nested lists of values."""
    if not row:
      return None
    values = [entry.get('v', '') for entry in row.get('f', [])]
    result = []
    for field, v in zip(schema, values):
      if 'type' not in field:
        raise bq_error.BigqueryCommunicationError(
            'Invalid response: missing type property'
        )
      if field['type'].upper() == 'RECORD':
        # Nested field.
        subfields = field.get('fields', [])
        if field.get('mode', 'NULLABLE').upper() == 'REPEATED':
          # Repeated and nested. Convert the array of v's of FV's.
          result.append([
              self._ConvertFromFV(subfields, subvalue.get('v', ''))
              for subvalue in v
          ])
        else:
          # Nested non-repeated field. Convert the nested f from FV.
          result.append(self._ConvertFromFV(subfields, v))
      elif field.get('mode', 'NULLABLE').upper() == 'REPEATED':
        # Repeated but not nested: an array of v's.
        result.append([subvalue.get('v', '') for subvalue in v])
      else:
        # Normal flat field.
        result.append(v)
    return result

  def __str__(self) -> str:
    return self._GetPrintContext()

  def __repr__(self) -> str:
    return self._GetPrintContext()

  def _GetPrintContext(self) -> str:
    """Returns context for what is being read."""
    raise NotImplementedError('Subclass must implement GetPrintContext')

  def _ReadOnePage(
      self,
      start_row: Optional[int],
      max_rows: Optional[int],
      page_token: Optional[str] = None,
      selected_fields: Optional[str] = None,
  ):
    """Read one page of data, up to max_rows rows.

    Assumes that the table is ready for reading. Will signal an error otherwise.

    Args:
      start_row: first row to read.
      max_rows: maximum number of rows to return.
      page_token: Optional. current page token.
      selected_fields: a subset of field to return.

    Returns:
      tuple of:
      rows: the actual rows of the table, in f,v format.
      page_token: the page token of the next page of results.
      schema: the schema of the table.
    """
    raise NotImplementedError('Subclass must implement _ReadOnePage')


class TableTableReader(_TableReader):
  """A TableReader that reads from a table."""

  def __init__(
      self,
      local_apiclient: discovery.Resource,
      max_rows_per_request: int,
      table_ref: bq_id_utils.ApiClientHelper.TableReference,
  ):
    self.table_ref = table_ref
    self.max_rows_per_request = max_rows_per_request
    self._apiclient = local_apiclient

  def _GetPrintContext(self) -> str:
    return '%r' % (self.table_ref,)

  def _ReadOnePage(
      self,
      start_row: Optional[int],
      max_rows: Optional[int],
      page_token: Optional[str] = None,
      selected_fields: Optional[str] = None,
  ):
    kwds = dict(self.table_ref)
    kwds['maxResults'] = max_rows
    if page_token:
      kwds['pageToken'] = page_token
    else:
      kwds['startIndex'] = start_row
    data = None
    if selected_fields is not None:
      kwds['selectedFields'] = selected_fields
    if data is None:
      data = self._apiclient.tabledata().list(**kwds).execute()
    page_token = data.get('pageToken', None)
    rows = data.get('rows', [])

    kwds = dict(self.table_ref)
    if selected_fields is not None:
      kwds['selectedFields'] = selected_fields
    table_info = self._apiclient.tables().get(**kwds).execute()
    schema = table_info.get('schema', {})

    return (rows, page_token, schema)


class JobTableReader(_TableReader):
  """A TableReader that reads from a completed job."""

  def __init__(
      self,
      local_apiclient: discovery.Resource,
      max_rows_per_request: int,
      job_ref: bq_id_utils.ApiClientHelper.JobReference,
  ):
    self.job_ref = job_ref
    self.max_rows_per_request = max_rows_per_request
    self._apiclient = local_apiclient

  def _GetPrintContext(self) -> str:
    return '%r' % (self.job_ref,)

  def _ReadOnePage(
      self,
      start_row: Optional[int],
      max_rows: Optional[int],
      page_token: Optional[str] = None,
      selected_fields: Optional[str] = None,
  ):
    kwds = dict(self.job_ref)
    kwds['maxResults'] = max_rows
    # Sets the timeout to 0 because we assume the table is already ready.
    kwds['timeoutMs'] = 0
    if page_token:
      kwds['pageToken'] = page_token
    else:
      kwds['startIndex'] = start_row
    data = self._apiclient.jobs().getQueryResults(**kwds).execute()
    if not data['jobComplete']:
      raise bq_error.BigqueryError('Job %s is not done' % (self,))
    page_token = data.get('pageToken', None)
    schema = data.get('schema', None)
    rows = data.get('rows', [])
    return (rows, page_token, schema)


class QueryTableReader(_TableReader):
  """A TableReader that reads from a completed query."""

  def __init__(
      self,
      local_apiclient: discovery.Resource,
      max_rows_per_request: int,
      job_ref: bq_id_utils.ApiClientHelper.JobReference,
      results,
  ):
    self.job_ref = job_ref
    self.max_rows_per_request = max_rows_per_request
    self._apiclient = local_apiclient
    self._results = results

  def _GetPrintContext(self) -> str:
    return '%r' % (self.job_ref,)

  def _ReadOnePage(
      self,
      start_row: Optional[int],
      max_rows: Optional[int],
      page_token: Optional[str] = None,
      selected_fields: Optional[str] = None,
  ):
    kwds = dict(self.job_ref) if self.job_ref else {}
    kwds['maxResults'] = max_rows
    # Sets the timeout to 0 because we assume the table is already ready.
    kwds['timeoutMs'] = 0
    if page_token:
      kwds['pageToken'] = page_token
    else:
      kwds['startIndex'] = start_row
    if not self._results['jobComplete']:
      raise bq_error.BigqueryError('Job %s is not done' % (self,))
    # DDL and DML statements return no rows, just delegate them to
    # getQueryResults.
    result_rows = self._results.get('rows', None)
    total_rows = self._results.get('totalRows', None)
    job_reference = self._results.get('jobReference', None)
    if job_reference is None and (
        total_rows is not None and int(total_rows) == 0
    ):
      # Handle the case when jobs.query requests with JOB_CREATION_OPTIONAL
      # return empty results. This will avoid a call to getQueryResults.
      schema = self._results.get('schema', None)
      rows = self._results.get('rows', [])
      page_token = None
    elif (
        total_rows is not None
        and result_rows is not None
        and start_row is not None
        and len(result_rows) >= min(int(total_rows), start_row + max_rows)
    ):
      page_token = self._results.get('pageToken', None)
      if len(result_rows) < int(total_rows) and page_token is None:
        raise bq_error.BigqueryError(
            'Synchronous query %s did not return all rows, yet it did not'
            ' return a page token' % (self,)
        )
      schema = self._results.get('schema', None)
      rows = self._results.get('rows', [])
    else:
      data = self._apiclient.jobs().getQueryResults(**kwds).execute()
      if not data['jobComplete']:
        raise bq_error.BigqueryError('Job %s is not done' % (self,))
      page_token = data.get('pageToken', None)
      schema = data.get('schema', None)
      rows = data.get('rows', [])
    return (rows, page_token, schema)
