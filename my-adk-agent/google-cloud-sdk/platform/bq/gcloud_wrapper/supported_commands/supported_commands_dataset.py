#!/usr/bin/env python
"""The supported gcloud dataset commands in BQ CLI."""

from typing import List

from gcloud_wrapper import bq_to_gcloud_config_classes

FlagMapping = bq_to_gcloud_config_classes.FlagMapping
UnsupportedFlagMapping = bq_to_gcloud_config_classes.UnsupportedFlagMapping
CommandMapping = bq_to_gcloud_config_classes.CommandMapping


_ACLS_TABLE_LABEL = (
    'access.format('
    '"Owners:\n  {0}\nWriters:\n  {1}\nReaders:\n  {1}",'
    '[].filter("role:OWNER").map(1).'
    'extract("specialGroup","userByEmail").map(1).list()'
    '.join(sep=\\",\n  \\"),'
    '[].filter("role:WRITER").map(1).'
    'extract("specialGroup","userByEmail").map(1).list()'
    '.join(sep=\\",\n  \\"),'
    '[].filter("role:READER").map(1).'
    'extract("specialGroup","userByEmail").map(1).list()'
    '.join(sep=\\",\n  \\")):label=ACLs:wrap=75'
)


def _json_mapping_list(
    gcloud_json: bq_to_gcloud_config_classes.NestedStrDict,
    _: str,
) -> bq_to_gcloud_config_classes.NestedStrDict:
  return {
      'kind': 'bigquery#dataset',
      'id': gcloud_json['id'],
      'datasetReference': gcloud_json['datasetReference'],
      'location': gcloud_json['location'],
      'type': gcloud_json['type'],
  }


def _json_mapping_show(
    gcloud_json: bq_to_gcloud_config_classes.NestedStrDict,
    bq_format: str,
) -> bq_to_gcloud_config_classes.NestedStrDict:
  """Returns the dataset show json mapping."""
  keys = [
      'kind',
      'etag',
      'id',
      'selfLink',
      'datasetReference',
      'access',
      'creationTime',
      'lastModifiedTime',
      'location',
      'type',
      'maxTimeTravelHours',
  ]
  if bq_format == 'prettyjson':
    keys.sort()
  return {key: gcloud_json[key] for key in keys}


def _create_status_mapping(
    original_status: str, identifier: str, project_id: str
) -> str:
  if original_status.startswith('Created dataset'):
    return f"Dataset '{project_id}:{identifier}' successfully created."
  return original_status


_DATASETS = 'datasets'


SUPPORTED_COMMANDS_DATASET: List[CommandMapping] = [
    CommandMapping(
        resource=_DATASETS,
        bq_command='ls',
        gcloud_command=['alpha', 'bq', 'datasets', 'list'],
        flag_mapping_list=[
            FlagMapping('max_results', 'limit'),
            FlagMapping('all', 'all'),
        ],
        table_projection='datasetReference.datasetId:label=datasetId',
        csv_projection='datasetReference.datasetId:label=dataset_id',
        json_mapping=_json_mapping_list,
    ),
    CommandMapping(
        resource=_DATASETS,
        bq_command='show',
        gcloud_command=['alpha', 'bq', 'datasets', 'describe'],
        table_projection=(
            'lastModifiedTime.date('
            'unit=1000,tz=LOCAL,format="%d %b %H:%M:%S"'
            '):label="Last modified",'
            f'{_ACLS_TABLE_LABEL},'
            'labels:label=Labels,'
            'type:label=Type,'
            'maxTimeTravelHours:label="Max time travel (Hours)"'
        ),
        json_mapping=_json_mapping_show,
    ),
    CommandMapping(
        resource=_DATASETS,
        bq_command='mk',
        gcloud_command=['alpha', 'bq', 'datasets', 'create'],
        flag_mapping_list=[
            FlagMapping('force', 'overwrite'),
            FlagMapping('description', 'description'),
            UnsupportedFlagMapping(
                'location',
                'The gcloud dataset create command does not support the'
                ' location flag.',
            ),
        ],
        status_mapping=_create_status_mapping,
        print_resource=False,
    ),
    CommandMapping(
        resource=_DATASETS,
        bq_command='rm',
        gcloud_command=['alpha', 'bq', 'datasets', 'delete'],
        flag_mapping_list=[FlagMapping('recursive', 'remove-tables')],
        print_resource=False,
        no_prompts=True,
        status_mapping=lambda input, _, __: '',
    ),
]
