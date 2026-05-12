#!/usr/bin/env python
"""Legacy code that isn't split up into resource based clients."""

from collections.abc import Callable
import sys

from googleapiclient import discovery
from typing_extensions import TypeAlias

from clients import client_project
from clients import utils as bq_client_utils
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils


# This Callable annotation would cause a type error before Python 3.9.2, see
# https://docs.python.org/3/whatsnew/3.9.html#notable-changes-in-python-3-9-2.
if sys.version_info >= (3, 9, 2):
  GetApiClienFunction: TypeAlias = Callable[[], discovery.Resource]
else:
  GetApiClienFunction: TypeAlias = Callable


def get_object_info(
    apiclient: discovery.Resource,
    get_routines_api_client: GetApiClienFunction,
    get_models_api_client: GetApiClienFunction,
    reference,
):
  """Get all data returned by the server about a specific object."""
  # Projects are handled separately, because we only have
  # bigquery.projects.list.
  if isinstance(reference, bq_id_utils.ApiClientHelper.ProjectReference):
    max_project_results = 1000
    projects = client_project.list_projects(
        apiclient=apiclient, max_results=max_project_results
    )
    for project in projects:
      if bq_processor_utils.ConstructObjectReference(project) == reference:
        project['kind'] = 'bigquery#project'
        return project
    if len(projects) >= max_project_results:
      raise bq_error.BigqueryError(
          'Number of projects found exceeded limit, please instead run'
          ' gcloud projects describe %s' % (reference,),
      )
    raise bq_error.BigqueryNotFoundError(
        'Unknown %r' % (reference,), {'reason': 'notFound'}, []
    )

  if isinstance(reference, bq_id_utils.ApiClientHelper.JobReference):
    return apiclient.jobs().get(**dict(reference)).execute()
  elif isinstance(reference, bq_id_utils.ApiClientHelper.DatasetReference):
    request = dict(reference)
    request['accessPolicyVersion'] = (
        bq_client_utils.MAX_SUPPORTED_IAM_POLICY_VERSION
    )
    return apiclient.datasets().get(**request).execute()
  elif isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
    return apiclient.tables().get(**dict(reference)).execute()
  elif isinstance(reference, bq_id_utils.ApiClientHelper.ModelReference):
    return (
        get_models_api_client()
        .models()
        .get(
            projectId=reference.projectId,
            datasetId=reference.datasetId,
            modelId=reference.modelId,
        )
        .execute()
    )
  elif isinstance(reference, bq_id_utils.ApiClientHelper.RoutineReference):
    return (
        get_routines_api_client()
        .routines()
        .get(
            projectId=reference.projectId,
            datasetId=reference.datasetId,
            routineId=reference.routineId,
        )
        .execute()
    )
  else:
    raise bq_error.BigqueryTypeError(
        'Type of reference must be one of: ProjectReference, '
        'JobReference, DatasetReference, or TableReference'
    )
