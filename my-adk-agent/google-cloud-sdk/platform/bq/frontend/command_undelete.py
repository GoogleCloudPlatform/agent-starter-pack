#!/usr/bin/env python
"""The undelete command for the BQ CLI."""

import datetime

from absl import app
from absl import flags

from clients import client_dataset
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-args


class Undelete(bigquery_command.BigqueryCmd):
  """Undelete the dataset described by identifier."""

  usage = """bq undelete dataset"""
  command = 'undelete'

  def __init__(self, name: str, fv: flags.FlagValues):
    super().__init__(name, fv)
    flags.DEFINE_integer(
        'timestamp',
        None,
        'Optional. Time in milliseconds since the POSIX epoch that this replica'
        ' was marked for deletion. If not specified, it will undelete the most'
        ' recently deleted version.',
        flag_values=fv,
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str):
    """Undelete the dataset described by identifier.

    Always requires an identifier, unlike the show and ls commands.
    By default, also requires confirmation before undeleting.
    Supports:
     - timestamp[int]: This signifies the timestamp version of the dataset that
     needs to be restored, this should be in milliseconds

    Examples:
      bq undelete dataset
      bq undelete --timestamp 1714720875568 dataset
    """

    client = bq_cached_client.Client.Get()
    if not identifier:
      raise app.UsageError('Must provide an identifier for undelete.')
    dataset = bq_client_utils.GetDatasetReference(
        id_fallbacks=client, identifier=identifier
    )
    if self.timestamp:
      timestamp = datetime.datetime.fromtimestamp(
          self.timestamp / 1000, tz=datetime.timezone.utc
      )
    else:
      timestamp = None
    job = client_dataset.UndeleteDataset(
        client.apiclient, dataset, timestamp=timestamp
    )
    if job:
      print('Dataset undelete of %s successfully started' % (dataset,))
