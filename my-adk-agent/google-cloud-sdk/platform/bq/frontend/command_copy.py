#!/usr/bin/env python
"""The BigQuery CLI copy command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import time
from typing import List, Optional, Tuple

from absl import flags

import bq_flags
from clients import bigquery_client
from clients import client_dataset
from clients import client_job
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import utils as frontend_utils
from frontend import utils_flags
from frontend import utils_formatting
from utils import bq_error
from utils import bq_id_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Copy(bigquery_command.BigqueryCmd):
  usage = """cp [-n] <source_table>[,<source_table>]* <dest_table>"""
  command = 'cp'

  _NOTE = '**** NOTE! **** '
  _DATASET_NOT_FOUND = (
      'Dataset %s not found. Please enter a valid dataset name.'
  )
  _CROSS_REGION_WARNING = (
      'Warning: This operation is a cross-region copy operation. This may incur'
      ' additional charges.'
  )
  _SYNC_FLAG_ENABLED_WARNING = (
      'Warning: This operation is a cross-region copy operation. This may incur'
      ' additional charges and take a long time to complete.\nThis command is'
      ' running in sync mode. It is recommended to use async mode (-sync=false)'
      ' for cross-region copy operation.'
  )
  _CONFIRM_CROSS_REGION = 'cp: Proceed with cross-region copy of %s? [y/N]: '
  _CONFIRM_OVERWRITE = 'cp: Table %s already exists. Replace the table? [y/N]: '
  _NOT_COPYING = ' %s, exiting.'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Copy, self).__init__(name, fv)
    flags.DEFINE_boolean(
        'no_clobber',
        False,
        'Do not overwrite an existing table.',
        short_name='n',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'force',
        False,
        "Ignore existing destination tables, don't prompt.",
        short_name='f',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'append_table',
        False,
        'Append to an existing table.',
        short_name='a',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'destination_kms_key',
        None,
        'Cloud KMS key for encryption of the destination table data.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'snapshot',
        False,
        'Create a table snapshot of source table.',
        short_name='s',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'restore',
        False,
        'Restore table snapshot to a live table. Deprecated, please use clone '
        ' instead.',
        short_name='r',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'expiration',
        None,
        'Expiration time, in seconds from now, of the destination table.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'clone', False, 'Create a clone of source table.', flag_values=fv
    )
    self._ProcessCommandRc(fv)

  def _CheckAllSourceDatasetsInSameRegionAndGetFirstSourceRegion(
      self,
      client: bigquery_client.BigqueryClient,
      source_references: List[bq_id_utils.ApiClientHelper.TableReference],
  ) -> Tuple[bool, Optional[str]]:
    """Checks whether all source datasets are from same region.

    Args:
      client: Bigquery client
      source_references: Source reference

    Returns:
      true  - all source datasets are from the same region. Includes the
              scenario in which there is only one source dataset
      false - all source datasets are not from the same region.
    Raises:
      bq_error.BigqueryNotFoundError: If unable to compute the dataset
        region
    """
    all_source_datasets_in_same_region = True
    first_source_region = None
    for _, val in enumerate(source_references):
      source_dataset = val.GetDatasetReference()
      source_region = client_dataset.GetDatasetRegion(
          apiclient=client.apiclient,
          reference=source_dataset,
      )
      if source_region is None:
        raise bq_error.BigqueryNotFoundError(
            self._DATASET_NOT_FOUND % (str(source_dataset),),
            {'reason': 'notFound'},
            [],
        )
      if first_source_region is None:
        first_source_region = source_region
      elif first_source_region != source_region:
        all_source_datasets_in_same_region = False
        break
    return all_source_datasets_in_same_region, first_source_region

  def shouldContinueAfterCrossRegionCheck(
      self,
      client: bigquery_client.BigqueryClient,
      source_references: List[bq_id_utils.ApiClientHelper.TableReference],
      source_references_str: str,
      dest_reference: bq_id_utils.ApiClientHelper.TableReference,
      destination_region: str,
  ) -> bool:
    """Checks if it is a Cross Region Copy operation and obtains confirmation.

    Args:
      client: Bigquery client
      source_references: Source reference
      source_references_str: Source reference string
      dest_reference: Destination dataset reference
      destination_region: Destination dataset region

    Returns:
      true  - it is not a cross-region operation, or user has used force option,
              or cross-region operation is verified confirmed with user, or
              Insufficient permissions to query datasets for validation
      false - if user did not allow cross-region operation, or
              Dataset does not exist hence operation can't be performed.
    Raises:
      bq_error.BigqueryNotFoundError: If unable to compute the dataset
        region
    """
    destination_dataset = dest_reference.GetDatasetReference()

    try:
      all_source_datasets_in_same_region, first_source_region = (
          self._CheckAllSourceDatasetsInSameRegionAndGetFirstSourceRegion(
              client, source_references
          )
      )
      if destination_region is None:
        destination_region = client_dataset.GetDatasetRegion(
            apiclient=client.apiclient, reference=destination_dataset
        )
    except bq_error.BigqueryAccessDeniedError as err:
      print(
          'Unable to determine source or destination dataset location, skipping'
          ' cross-region validation: '
          + str(err)
      )
      return True
    if destination_region is None:
      raise bq_error.BigqueryNotFoundError(
          self._DATASET_NOT_FOUND % (str(destination_dataset),),
          {'reason': 'notFound'},
          [],
      )
    if all_source_datasets_in_same_region and (
        destination_region == first_source_region
    ):
      return True
    print(
        self._NOTE,
        '\n' + self._SYNC_FLAG_ENABLED_WARNING
        if bq_flags.SYNCHRONOUS_MODE.value
        else '\n' + self._CROSS_REGION_WARNING,
    )
    if self.force:
      return True
    if 'y' != frontend_utils.PromptYN(
        self._CONFIRM_CROSS_REGION % (source_references_str,)
    ):
      print(self._NOT_COPYING % (source_references_str,))
      return False
    return True

  def RunWithArgs(self, source_tables: str, dest_table: str) -> Optional[int]:
    """Copies one table to another.

    Examples:
      bq cp dataset.old_table dataset2.new_table
      bq cp --destination_kms_key=kms_key dataset.old_table dataset2.new_table
    """
    client = bq_cached_client.Client.Get()
    source_references = [
        bq_client_utils.GetTableReference(id_fallbacks=client, identifier=src)
        for src in source_tables.split(',')
    ]
    source_references_str = ', '.join(str(src) for src in source_references)
    dest_reference = bq_client_utils.GetTableReference(
        id_fallbacks=client, identifier=dest_table
    )

    if self.append_table:
      write_disposition = 'WRITE_APPEND'
      ignore_already_exists = True
    elif self.no_clobber:
      write_disposition = 'WRITE_EMPTY'
      ignore_already_exists = True
    else:
      write_disposition = 'WRITE_TRUNCATE'
      ignore_already_exists = False

    # Check if destination table exists, confirm overwrite
    destination_region = None
    if not ignore_already_exists and not self.force:
      destination_region = client_table.get_table_region(
          apiclient=client.apiclient, reference=dest_reference
      )
      if destination_region and 'y' != frontend_utils.PromptYN(
          self._CONFIRM_OVERWRITE % (dest_reference)
      ):
        print(self._NOT_COPYING % (source_references_str,))
        return 0

    if not self.shouldContinueAfterCrossRegionCheck(
        client,
        source_references,
        source_references_str,
        dest_reference,
        destination_region,
    ):
      return 0

    operation = 'copied'
    if self.snapshot:
      operation_type = 'SNAPSHOT'
      operation = 'snapshotted'
    elif self.restore:
      operation_type = 'RESTORE'
      operation = 'restored'
    elif self.clone:
      operation_type = 'CLONE'
      operation = 'cloned'
    else:
      operation_type = 'COPY'
    kwds = {
        'write_disposition': write_disposition,
        'ignore_already_exists': ignore_already_exists,
        'job_id': utils_flags.get_job_id_from_flags(),
        'operation_type': operation_type,
    }
    if bq_flags.LOCATION.value:
      kwds['location'] = bq_flags.LOCATION.value

    if self.destination_kms_key:
      kwds['encryption_configuration'] = {
          'kmsKeyName': self.destination_kms_key
      }
    if self.expiration:
      datetime_utc = datetime.datetime.utcfromtimestamp(
          int(self.expiration + time.time())
      )
      kwds['destination_expiration_time'] = frontend_utils.FormatRfc3339(
          datetime_utc
      )
    job = client_job.CopyTable(
        client, source_references, dest_reference, **kwds
    )
    if job is None:
      print("Table '%s' already exists, skipping" % (dest_reference,))
    elif not bq_flags.SYNCHRONOUS_MODE.value:
      self.PrintJobStartInfo(job)
    else:
      plurality = 's' if len(source_references) > 1 else ''
      print(
          "Table%s '%s' successfully %s to '%s'"
          % (plurality, source_references_str, operation, dest_reference)
      )
      # If we are here, the job succeeded, but print warnings if any.
      frontend_utils.PrintJobMessages(utils_formatting.format_job_info(job))
