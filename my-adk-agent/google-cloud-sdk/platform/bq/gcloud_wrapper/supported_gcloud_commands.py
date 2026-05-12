#!/usr/bin/env python
"""The gcloud delegators supported by the BQ CLI."""

import logging
from typing import List

from gcloud_wrapper import bq_to_gcloud_config_classes
from gcloud_wrapper.supported_commands.supported_commands_dataset import SUPPORTED_COMMANDS_DATASET
from gcloud_wrapper.supported_commands.supported_commands_migration_workflow import SUPPORTED_COMMANDS_MIGRATION_WORKFLOW
from gcloud_wrapper.supported_commands.supported_commands_project import SUPPORTED_COMMANDS_PROJECT


FlagMapping = bq_to_gcloud_config_classes.FlagMapping
UnsupportedFlagMapping = bq_to_gcloud_config_classes.UnsupportedFlagMapping
CommandMapping = bq_to_gcloud_config_classes.CommandMapping


def _bq_apilog_to_gcloud_verbosity(apilog: str) -> str:
  if apilog not in ('', '-', '1', 'true', 'stdout'):
    logging.warning(
        'Gcloud only supports logging to stdout and apilog is set to %s', apilog
    )
  return 'debug'


def _bq_verbosity_to_gcloud_verbosity(verbosity: int) -> str:
  """Returns the gcloud verbosity level for the given bq verbosity level."""
  if verbosity <= -3:
    # The `critical` value is used instead of `fatal` in gcloud.
    return 'critical'
  elif verbosity == -2:
    return 'error'
  elif verbosity == -1:
    return 'warning'
  elif verbosity == 0:
    return 'info'
  elif verbosity >= 1:
    return 'debug'
  raise ValueError(f'Unknown verbosity level: {verbosity}')


# Note: Then `format` flag is not included here since it's mapping is a lot more
# complicated and requires taking into account the command being executed. so it
# is handled as part of the implementation.
SUPPORTED_GLOBAL_FLAGS: List[FlagMapping] = [
    FlagMapping('project_id', 'project'),
    FlagMapping('httplib2_debuglevel', 'log-http', lambda x: x > 0),
    # TODO(b/355324165): Handle condition when both flags are used.
    FlagMapping('apilog', 'verbosity', _bq_apilog_to_gcloud_verbosity),
    FlagMapping('verbosity', 'verbosity', _bq_verbosity_to_gcloud_verbosity),
    # Unsupported flags.
    UnsupportedFlagMapping(
        'mtls',
        'The `mtls` flag cannot be used directly when delegating to gcloud. It'
        ' must be configured in the `gcloud` config and it will be loaded'
        ' during execution',
    ),
]


SUPPORTED_COMMANDS: List[CommandMapping] = (
    SUPPORTED_COMMANDS_DATASET
    + SUPPORTED_COMMANDS_PROJECT
    + SUPPORTED_COMMANDS_MIGRATION_WORKFLOW
)
