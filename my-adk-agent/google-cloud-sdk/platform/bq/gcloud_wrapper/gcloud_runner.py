#!/usr/bin/env python
"""Utilities to run gcloud for the BQ CLI."""

import logging
import os
import subprocess
import sys
from typing import List, Optional

from typing_extensions import TypeAlias

from pyglib import resources

if sys.version_info >= (3, 9):
  GcloudPopen: TypeAlias = subprocess.Popen[str]
else:
  # Before python 3.9 the type `subprocess.Popen[str]` is unsupported.
  GcloudPopen: TypeAlias = subprocess.Popen  # pylint: disable=g-bare-generic

_gcloud_path = None


def _get_gcloud_path() -> str:
  """Returns the string to use to call gcloud."""
  global _gcloud_path
  if _gcloud_path:
    logging.info('Found cached gcloud path: %s', _gcloud_path)
    return _gcloud_path

  if 'nt' == os.name:
    binary = 'gcloud.cmd'
  else:
    binary = 'gcloud'

  # If a gcloud binary has been bundled with this code then use that version
  # instead of the system installed version.
  try:
    binary = resources.GetResourceFilename(
        'google3/cloud/sdk/gcloud/gcloud.par'
    )
  except FileNotFoundError:
    pass

  logging.info('Found gcloud path: %s', binary)
  _gcloud_path = binary
  return binary


def run_gcloud_command(
    cmd: List[str], stderr: Optional[int] = None
) -> GcloudPopen:
  """Runs the given gcloud command and returns the Popen object."""
  gcloud_path = _get_gcloud_path()
  logging.info('Running gcloud command: %s %s', gcloud_path, ' '.join(cmd))
  return subprocess.Popen(
      [gcloud_path] + cmd,
      stdout=subprocess.PIPE,
      stderr=stderr,
      universal_newlines=True,
  )
