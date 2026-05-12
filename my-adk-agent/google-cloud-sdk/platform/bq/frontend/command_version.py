#!/usr/bin/env python
"""The BigQuery CLI version command."""

from typing import Optional

import bq_utils
from frontend import bigquery_command

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Version(bigquery_command.BigqueryCmd):
  usage = """version"""
  command = 'version'

  def _NeedsInit(self) -> bool:
    """If just printing the version, don't run `init` first."""
    return False

  def RunWithArgs(self) -> Optional[int]:
    """Return the version of bq."""
    print('This is BigQuery CLI %s' % (bq_utils.VERSION_NUMBER,))
