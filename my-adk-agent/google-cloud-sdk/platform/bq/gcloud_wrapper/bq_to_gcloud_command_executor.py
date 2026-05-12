#!/usr/bin/env python
"""An adapter that takes a bq command with flags and executes it with gcloud."""

from typing import Dict, Optional, Union

from absl import flags
from absl import logging

import bq_flags
from gcloud_wrapper import bq_to_gcloud_adapter


# TODO(user): Close out design discussion in comment thread from cl/659752136.
# Should this be here, or part of `GlobalFlagsMap.map_to_gcloud_global_flags`?
def _unpack_bq_global_flags() -> Dict[str, Union[str, int, bool]]:
  """Returns the bq_global_flags from the bq flags."""
  bq_global_flags = {}

  def unpack_flag_holder(flag_holder: flags.FlagHolder, key_name: str) -> None:
    if flag_holder.present and flag_holder.value is not None:
      bq_global_flags[key_name] = flag_holder.value

  unpack_flag_holder(bq_flags.FORMAT, 'format')
  unpack_flag_holder(bq_flags.PROJECT_ID, 'project_id')
  unpack_flag_holder(bq_flags.HTTPLIB2_DEBUGLEVEL, 'httplib2_debuglevel')
  try:
    unpack_flag_holder(logging.VERBOSITY, 'verbosity')
  except AttributeError:
    # Some versions of absl.logging don't have VERBOSITY.
    pass
  unpack_flag_holder(bq_flags.APILOG, 'apilog')

  # Unsupported flags
  unpack_flag_holder(bq_flags.MTLS, 'mtls')

  return bq_global_flags


def run_bq_command_using_gcloud(
    resource: str,
    bq_command: str,
    bq_command_flags: Dict[str, str],
    identifier: Optional[str] = None,
) -> int:
  bq_global_flags = _unpack_bq_global_flags()
  dry_run = False  # pylint: disable=unused-variable
  return bq_to_gcloud_adapter.run_bq_command_using_gcloud(
      resource=resource,
      bq_command=bq_command,
      bq_global_flags=bq_global_flags,
      bq_command_flags=bq_command_flags,
      identifier=identifier,
      dry_run=dry_run,
  )
