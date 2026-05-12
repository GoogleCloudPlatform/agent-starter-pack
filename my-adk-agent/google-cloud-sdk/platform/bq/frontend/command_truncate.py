#!/usr/bin/env python
"""The BigQuery CLI truncate command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import Optional

from absl import app
from absl import flags

import bq_flags
from clients import client_job
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Truncate(bigquery_command.BigqueryCmd):  # pylint: disable=missing-docstring
  usage = """bq truncate project_id:dataset[.table] [--timestamp] [--dry_run] [--overwrite] [--skip_fully_replicated_tables]
"""
  command = 'truncate'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Truncate, self).__init__(name, fv)
    flags.DEFINE_integer(
        'timestamp',
        None,
        'Optional timestamp to which table(s) will be truncated. Specified as '
        'milliseconds since epoch.',
        short_name='t',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'dry_run',
        None,
        'No-op that simply prints out information and the recommended '
        'timestamp without modifying tables or datasets.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'overwrite',
        False,
        'Overwrite existing tables. Otherwise timestamp will be appended to '
        'all output table names.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'skip_fully_replicated_tables',
        True,
        'Skip tables that are fully replicated (synced) and do not need to be '
        'truncated back to a point in time. This could result in datasets that '
        'have tables synchronized to different points in time, but will '
        'require less data to be re-loaded',
        short_name='s',
        flag_values=fv,
    )

    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str = '') -> Optional[int]:
    # pylint: disable=g-doc-exception
    """Truncates table/dataset/project to a particular timestamp.

    Examples:
      bq truncate project_id:dataset
      bq truncate --overwrite project_id:dataset --timestamp 123456789
      bq truncate --skip_fully_replicated_tables=false project_id:dataset
    """
    client = bq_cached_client.Client.Get()

    if identifier:
      reference = bq_client_utils.GetReference(
          id_fallbacks=client, identifier=identifier.strip()
      )
    else:
      raise app.UsageError('Must specify one of project, dataset or table')

    self.truncated_table_count = 0
    self.skipped_table_count = 0
    self.failed_table_count = 0
    status = []
    if self.timestamp and not self.dry_run:
      print(
          'Truncating to user specified timestamp %s.(Not skipping fully'
          ' replicated tables.)'
          % self.timestamp
      )
      if isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
        all_tables = [reference]
      else:
        if isinstance(reference, bq_id_utils.ApiClientHelper.DatasetReference):
          all_tables = list(
              map(
                  lambda x: bq_client_utils.GetReference(
                      id_fallbacks=client, identifier=x['id']
                  ),
                  client_table.list_tables(
                      apiclient=client.apiclient,
                      reference=reference,
                      max_results=1000 * 1000,
                  ),
              )
          )
      for a_table in all_tables:
        try:
          status.append(
              self._TruncateTable(a_table, str(self.timestamp), False)
          )
        except bq_error.BigqueryError as e:
          print(e)
          status.append((self._formatOutputString(a_table, 'Failed')))
          self.failed_table_count += 1
    else:
      if isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
        all_table_infos = self._GetTableInfo(reference)
      else:
        if isinstance(reference, bq_id_utils.ApiClientHelper.DatasetReference):
          all_table_infos = self._GetTableInfosFromDataset(reference)
      try:
        recovery_timestamp = min(
            list(map(self._GetRecoveryTimestamp, all_table_infos))
        )
      except (ValueError, bq_error.BigqueryTypeError):
        recovery_timestamp = None
      # Error out if we can't figure out a recovery timestamp
      # This can happen in following cases:
      # 1. No multi_site_info present for a table because no commit has been
      #  made to the table.
      # 2. No secondary site is present.
      if not recovery_timestamp:
        raise app.UsageError(
            'Unable to figure out a recovery timestamp for %s. Exiting.'
            % reference
        )
      print('Recommended timestamp to truncate to is %s' % recovery_timestamp)

      for a_table in all_table_infos:
        if not hasattr(reference, 'datasetId'):
          raise AttributeError('Missing `datasetId` on reference.')
        try:
          table_reference = bq_id_utils.ApiClientHelper.TableReference.Create(
              projectId=reference.projectId,
              datasetId=reference.datasetId,
              tableId=a_table['name'],
          )
          status.append(
              self._TruncateTable(
                  table_reference,
                  str(recovery_timestamp),
                  a_table['fully_replicated'],
              )
          )
        except bq_error.BigqueryError as e:
          print(e)
          status.append((self._formatOutputString(table_reference, 'Failed')))
          self.failed_table_count += 1
    print(
        '%s tables truncated, %s tables failed to truncate, %s tables skipped'
        % (
            self.truncated_table_count,
            self.failed_table_count,
            self.skipped_table_count,
        )
    )
    print(*status, sep='\n')

  def _GetTableInfosFromDataset(
      self, dataset_reference: bq_id_utils.ApiClientHelper.DatasetReference
  ):

    # Find minimum of second maximum(latest_replicated_time) for all tables in
    # the dataset and if they are fully replicated.
    recovery_timestamp_for_dataset_query = ("""SELECT
  TABLE_NAME,
  UNIX_MILLIS(replicated_time_at_remote_site),
  CASE
    WHEN last_update_time <= min_latest_replicated_time THEN TRUE
  ELSE
  FALSE
END
  AS fully_replicated
FROM (
  SELECT
    TABLE_NAME,
    multi_site_info.last_update_time,
    ARRAY_AGG(site_info.latest_replicated_time
    ORDER BY
      latest_replicated_time DESC)[safe_OFFSET(1)] AS replicated_time_at_remote_site,
    ARRAY_AGG(site_info.latest_replicated_time
    ORDER BY
      latest_replicated_time ASC)[safe_OFFSET(0)] AS min_latest_replicated_time
  FROM
    %s.INFORMATION_SCHEMA.TABLES t,
    t.multi_site_info.site_info
  GROUP BY
    1,
    2)""") % dataset_reference.datasetId
    return self._ReadTableInfo(
        recovery_timestamp_for_dataset_query, 1000 * 1000
    )

  def _GetTableInfo(
      self, table_reference: bq_id_utils.ApiClientHelper.TableReference
  ):

    # Find second maximum of latest_replicated_time across all sites for this
    # table and if the table is fully replicated
    recovery_timestamp_for_table_query = ("""SELECT
  TABLE_NAME,
  UNIX_MILLIS(replicated_time_at_remote_site),
  CASE
    WHEN last_update_time <= min_latest_replicated_time THEN TRUE
  ELSE
  FALSE
END
  AS fully_replicated
FROM (
  SELECT
    TABLE_NAME,
    multi_site_info.last_update_time,
    ARRAY_AGG(site_info.latest_replicated_time
    ORDER BY
      latest_replicated_time DESC)[safe_OFFSET(1)] AS replicated_time_at_remote_site,
    ARRAY_AGG(site_info.latest_replicated_time
    ORDER BY
      latest_replicated_time ASC)[safe_OFFSET(0)] AS min_latest_replicated_time
  FROM
    %s.INFORMATION_SCHEMA.TABLES t,
    t.multi_site_info.site_info
  WHERE
    TABLE_NAME = '%s'
  GROUP BY
    1,
    2 )""") % (table_reference.datasetId, table_reference.tableId)
    return self._ReadTableInfo(recovery_timestamp_for_table_query, row_count=1)

  def _GetRecoveryTimestamp(self, table_info) -> Optional[int]:
    return (
        int(table_info['recovery_timestamp'])
        if table_info['recovery_timestamp']
        else None
    )

  def _ReadTableInfo(self, query: str, row_count: int):
    client = bq_cached_client.Client.Get()
    try:
      job = client_job.Query(client, query, use_legacy_sql=False)
    except bq_error.BigqueryError as e:
      # TODO(b/324243535): Correct this typing.
      # pytype: disable=attribute-error
      if 'Name multi_site_info not found' in e.error['message']:
        # pytype: enable=attribute-error
        raise app.UsageError(
            'This functionality is not enabled for the current project.'
        )
      else:
        raise e
    all_table_infos = []
    if not bq_client_utils.IsFailedJob(job):
      _, rows = client_job.ReadSchemaAndJobRows(
          client, job['jobReference'], start_row=0, max_rows=row_count
      )
      for i in range(len(rows)):
        table_info = {}
        table_info['name'] = rows[i][0]
        table_info['recovery_timestamp'] = rows[i][1]
        table_info['fully_replicated'] = rows[i][2] == 'true'
        all_table_infos.append(table_info)
      return all_table_infos

  def _formatOutputString(
      self,
      table_reference: bq_id_utils.ApiClientHelper.TableReference,
      status: str,
  ) -> str:
    return '%s %200s' % (table_reference, status)

  def _TruncateTable(
      self,
      table_reference: bq_id_utils.ApiClientHelper.TableReference,
      recovery_timestamp: str,
      is_fully_replicated: bool,
  ) -> str:
    client = bq_cached_client.Client.Get()
    kwds = {}
    if not self.overwrite:
      dest = bq_id_utils.ApiClientHelper.TableReference.Create(
          projectId=table_reference.projectId,
          datasetId=table_reference.datasetId,
          tableId='_'.join(
              [table_reference.tableId, 'TRUNCATED_AT', recovery_timestamp]
          ),
      )
    else:
      dest = table_reference

    if self.skip_fully_replicated_tables and is_fully_replicated:
      self.skipped_table_count += 1
      return self._formatOutputString(
          table_reference, 'Fully replicated...Skipped'
      )
    if self.dry_run:
      return self._formatOutputString(
          dest, 'will be Truncated@%s' % recovery_timestamp
      )
    kwds = {
        'write_disposition': 'WRITE_TRUNCATE',
        'ignore_already_exists': False,
        'operation_type': 'COPY',
    }
    if bq_flags.LOCATION.value:
      kwds['location'] = bq_flags.LOCATION.value
    source_table = bq_client_utils.GetTableReference(
        id_fallbacks=client,
        identifier='%s@%s' % (table_reference, recovery_timestamp),
    )
    job_ref = ' '
    try:
      job = client_job.CopyTable(client, [source_table], dest, **kwds)
      if job is None:
        self.failed_table_count += 1
        return self._formatOutputString(dest, 'Failed')
      job_ref = bq_processor_utils.ConstructObjectReference(job)
      self.truncated_table_count += 1
      return self._formatOutputString(dest, 'Successful %s ' % job_ref)
    except bq_error.BigqueryError as e:
      print(e)
      self.failed_table_count += 1
      return self._formatOutputString(dest, 'Failed %s ' % job_ref)
