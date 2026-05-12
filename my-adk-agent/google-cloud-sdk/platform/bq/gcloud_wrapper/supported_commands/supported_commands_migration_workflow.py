#!/usr/bin/env python
"""The supported gcloud migration workflow commands in BQ CLI."""

from typing import List

from gcloud_wrapper import bq_to_gcloud_config_classes

FlagMapping = bq_to_gcloud_config_classes.FlagMapping
UnsupportedFlagMapping = bq_to_gcloud_config_classes.UnsupportedFlagMapping
CommandMapping = bq_to_gcloud_config_classes.CommandMapping


def _synchronous_progress_message_matcher(raw_output: str) -> bool:
  return raw_output.startswith(
      'Running migration workflow'
  ) or raw_output.startswith('......')


# --synchronous_mode in BQ CLI should be mapped to --async in gcloud.
_SYNCHRONOUS_MODE_MAPPER = lambda x: not x

_MIGRATION_WORKFLOWS = 'migration_workflows'

SUPPORTED_COMMANDS_MIGRATION_WORKFLOW: List[CommandMapping] = [
    CommandMapping(
        resource=_MIGRATION_WORKFLOWS,
        bq_command='ls',
        gcloud_command=['bq', 'migration-workflows', 'list'],
        flag_mapping_list=[
            FlagMapping('location', 'location'),
            FlagMapping('max_results', 'limit'),
        ],
        table_projection='name,displayName,state,createTime,lastUpdateTime',
        csv_projection='name,displayName:label=display_name,state,createTime:label=create_time,lastUpdateTime:label=last_update_time',
    ),
    CommandMapping(
        resource=_MIGRATION_WORKFLOWS,
        bq_command='show',
        gcloud_command=['bq', 'migration-workflows', 'describe'],
        table_projection=(
            'name:label=Name,'
            'displayName:label="Display Name",'
            'state:label=State,'
            'createTime:label="Create Time",'
            'lastUpdateTime:label="Last Update Time"'
        ),
    ),
    CommandMapping(
        resource=_MIGRATION_WORKFLOWS,
        bq_command='mk',
        gcloud_command=['bq', 'migration-workflows', 'create'],
        flag_mapping_list=[
            FlagMapping('location', 'location'),
            FlagMapping('config_file', 'config-file'),
            FlagMapping(
                'sync', 'async', bq_to_gcloud_mapper=_SYNCHRONOUS_MODE_MAPPER
            ),
            FlagMapping(
                'synchronous_mode',
                'async',
                bq_to_gcloud_mapper=_SYNCHRONOUS_MODE_MAPPER,
            ),
        ],
        table_projection=(
            'name:label=Name,'
            'displayName:label="Display Name",'
            'state:label=State,'
            'createTime:label="Create Time",'
            'lastUpdateTime:label="Last Update Time"'
        ),
        synchronous_progress_message_matcher=_synchronous_progress_message_matcher,
    ),
    CommandMapping(
        resource=_MIGRATION_WORKFLOWS,
        bq_command='rm',
        gcloud_command=['bq', 'migration-workflows', 'delete'],
        print_resource=False,
        no_prompts=True,
        status_mapping=lambda *args: '',  # No message printed for deletion.
    ),
]
