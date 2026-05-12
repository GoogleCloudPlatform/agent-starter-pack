#!/usr/bin/env python
"""The BigQuery CLI partition command."""

import datetime
from typing import Optional, cast

from absl import flags

import bq_flags
from clients import client_job
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import utils as frontend_utils
from frontend import utils_flags
from frontend import utils_formatting
from utils import bq_id_utils
from pyglib import stringutil

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Partition(bigquery_command.BigqueryCmd):  # pylint: disable=missing-docstring
  usage = """partition source_prefix destination_table"""
  command = 'partition'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Partition, self).__init__(name, fv)
    flags.DEFINE_boolean(
        'no_clobber',
        False,
        'Do not overwrite an existing partition.',
        short_name='n',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'time_partitioning_type',
        'DAY',
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
    self._ProcessCommandRc(fv)

  def RunWithArgs(
      self, source_prefix: str, destination_table: str
  ) -> Optional[int]:
    """Copies source tables into partitioned tables.

    Usage:
    bq partition <source_table_prefix> <destination_partitioned_table>

    Copies tables of the format <source_table_prefix><time_unit_suffix> to a
    destination partitioned table, with the <time_unit_suffix> of the source
    tables becoming the partition ID of the destination table partitions. The
    suffix is <YYYYmmdd> by default, <YYYY> if the time_partitioning_type flag
    is set to YEAR, <YYYYmm> if set to MONTH, and <YYYYmmddHH> if set to HOUR.

    If the destination table does not exist, one will be created with
    a schema and that matches the last table that matches the supplied
    prefix.

    Examples:
      bq partition dataset1.sharded_ dataset2.partitioned_table
    """

    client = bq_cached_client.Client.Get()
    formatter = utils_flags.get_formatter_from_flags()

    source_table_prefix = bq_client_utils.GetReference(
        id_fallbacks=client, identifier=source_prefix
    )
    bq_id_utils.typecheck(
        source_table_prefix,
        bq_id_utils.ApiClientHelper.TableReference,
        'Cannot determine table associated with "%s"' % (source_prefix,),
        is_usage_error=True,
    )
    # TODO(b/333595633): Fix typecheck so the response is cast.
    source_table_prefix = cast(
        bq_id_utils.ApiClientHelper.TableReference, source_table_prefix
    )
    destination_table = bq_client_utils.GetReference(
        id_fallbacks=client, identifier=destination_table
    )
    bq_id_utils.typecheck(
        destination_table,
        bq_id_utils.ApiClientHelper.TableReference,
        'Cannot determine table associated with "%s"' % (destination_table,),
        is_usage_error=True,
    )
    # TODO(b/333595633): Fix typecheck so the response is cast.
    destination_table = cast(
        bq_id_utils.ApiClientHelper.TableReference, destination_table
    )

    source_dataset = source_table_prefix.GetDatasetReference()
    source_id_prefix = stringutil.ensure_str(source_table_prefix.tableId)
    source_id_len = len(source_id_prefix)

    job_id_prefix = utils_flags.get_job_id_from_flags()
    if isinstance(job_id_prefix, bq_client_utils.JobIdGenerator):
      job_id_prefix = job_id_prefix.Generate(
          [source_table_prefix, destination_table]
      )

    destination_dataset = destination_table.GetDatasetReference()

    utils_formatting.configure_formatter(
        formatter, bq_id_utils.ApiClientHelper.TableReference
    )
    results = map(
        utils_formatting.format_table_info,
        client_table.list_tables(
            apiclient=client.apiclient,
            reference=source_dataset,
            max_results=1000 * 1000,
        ),
    )

    partition_ids = []
    representative_table = None

    time_format = '%Y%m%d'  # default to format for DAY
    if self.time_partitioning_type == 'HOUR':
      time_format = '%Y%m%d%H'
    elif self.time_partitioning_type == 'MONTH':
      time_format = '%Y%m'
    elif self.time_partitioning_type == 'YEAR':
      time_format = '%Y'

    for result in results:
      table_id = stringutil.ensure_str(result['tableId'])
      if table_id.startswith(source_id_prefix):
        suffix = table_id[source_id_len:]
        try:
          partition_id = datetime.datetime.strptime(suffix, time_format)
          partition_ids.append(partition_id.strftime(time_format))
          representative_table = result
        except ValueError:
          pass

    if not representative_table:
      print('No matching source tables found')
      return

    print(
        'Copying %d source partitions to %s'
        % (len(partition_ids), destination_table)
    )

    # Check to see if we need to create the destination table.
    if not client_table.table_exists(
        apiclient=client.apiclient,
        reference=destination_table,
    ):
      source_table_id = representative_table['tableId']
      source_table_ref = source_dataset.GetTableReference(source_table_id)
      source_table_schema = client_table.get_table_schema(
          apiclient=client.apiclient,
          table_dict=source_table_ref,
      )
      # Get fields in the schema.
      if source_table_schema:
        source_table_schema = source_table_schema['fields']

      time_partitioning = frontend_utils.ParseTimePartitioning(
          self.time_partitioning_type, self.time_partitioning_expiration
      )

      print(
          'Creating table: %s with schema from %s and partition spec %s'
          % (destination_table, source_table_ref, time_partitioning)
      )

      client_table.create_table(
          apiclient=client.apiclient,
          reference=destination_table,
          schema=source_table_schema,
          time_partitioning=time_partitioning,
      )
      print('%s successfully created.' % (destination_table,))

    for partition_id in partition_ids:
      destination_table_id = '%s$%s' % (destination_table.tableId, partition_id)
      source_table_id = '%s%s' % (source_id_prefix, partition_id)
      current_job_id = '%s%s' % (job_id_prefix, partition_id)

      source_table = source_dataset.GetTableReference(source_table_id)
      destination_partition = destination_dataset.GetTableReference(
          destination_table_id
      )

      avoid_copy = False
      if self.no_clobber:
        maybe_destination_partition = client_table.table_exists(
            apiclient=client.apiclient,
            reference=destination_partition,
        )
        avoid_copy = (
            maybe_destination_partition
            and int(maybe_destination_partition['numBytes']) > 0
        )

      if avoid_copy:
        print("Table '%s' already exists, skipping" % (destination_partition,))
      else:
        print('Copying %s to %s' % (source_table, destination_partition))
        kwds = {
            'write_disposition': 'WRITE_TRUNCATE',
            'job_id': current_job_id,
        }
        if bq_flags.LOCATION.value:
          kwds['location'] = bq_flags.LOCATION.value
        job = client_job.CopyTable(
            client, [source_table], destination_partition, **kwds
        )
        if not bq_flags.SYNCHRONOUS_MODE.value:
          self.PrintJobStartInfo(job)
        else:
          print(
              'Successfully copied %s to %s'
              % (source_table, destination_partition)
          )
