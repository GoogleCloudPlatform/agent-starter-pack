#!/usr/bin/env python
"""The supported gcloud project commands in BQ CLI."""

from typing import List

from gcloud_wrapper import bq_to_gcloud_config_classes

FlagMapping = bq_to_gcloud_config_classes.FlagMapping
UnsupportedFlagMapping = bq_to_gcloud_config_classes.UnsupportedFlagMapping
CommandMapping = bq_to_gcloud_config_classes.CommandMapping


_PROJECTS = 'projects'


def project_json_mapping(
    gcloud_json: bq_to_gcloud_config_classes.NestedStrDict,
    _: str,
) -> bq_to_gcloud_config_classes.NestedStrDict:
  return {
      'kind': 'bigquery#project',
      'id': gcloud_json['projectId'],
      'numericId': gcloud_json['projectNumber'],
      'projectReference': {
          'projectId': gcloud_json['projectId'],
      },
      'friendlyName': gcloud_json['name'],
  }


SUPPORTED_COMMANDS_PROJECT: List[CommandMapping] = [
    # Note: The API used by the BQ CLI is the BQ API and this has a different
    # permissions structure that can cause issues during migration. This is
    # similar to some issues seen when using the BQ UI vs using the Simba
    # drivers.
    CommandMapping(
        resource=_PROJECTS,
        bq_command='ls',
        gcloud_command=[
            'projects',
            'list',
            # The BQ CLI uses the BQ API to list projects and that lists
            # projects in alphabetical order by project id.
            '--sort-by=projectId',
        ],
        flag_mapping_list=[FlagMapping('max_results', 'limit')],
        table_projection='projectId:label=projectId,name:label="friendlyName"',
        csv_projection='projectId:label=project_id,name:label=friendly_name',
        json_mapping=project_json_mapping,
    ),
]
