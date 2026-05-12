#!/usr/bin/env python
"""The BQ CLI `info` command."""

import bq_utils
from frontend import bigquery_command
from gcloud_wrapper import gcloud_runner

# The usage string acts as the docstring for the class.
# pylint: disable=missing-class-docstring


class Info(bigquery_command.BigqueryCmd):
  usage = """info"""
  command = 'info'

  def _NeedsInit(self) -> bool:
    """If just printing known versions, don't run `init` first."""
    return False

  def RunWithArgs(self) -> None:
    """Return the execution information of bq."""
    print(bq_utils.GetInfoString())

    proc = gcloud_runner.run_gcloud_command(['info'])
    if proc.stdout:
      print('With the following gcloud configuration:\n')
      print(''.join(proc.stdout.readlines()))
