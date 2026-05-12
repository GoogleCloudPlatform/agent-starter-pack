#!/usr/bin/env python
"""The BigQuery CLI routine client library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import Optional

from googleapiclient import discovery

from utils import bq_error
from utils import bq_id_utils


def ListRoutines(
    routines_api_client: discovery.Resource,
    reference: 'bq_id_utils.ApiClientHelper.DatasetReference',
    max_results: int,
    page_token: str,
    filter_expression: str,
):
  """Lists routines for the given dataset reference.

  Arguments:
    routines_api_client: the api client used to make the request.
    reference: Reference to the dataset.
    max_results: Number of results to return.
    page_token: Token to retrieve the next page of results.
    filter_expression: An expression for filtering routines.

  Returns:
    A dict that contains entries:
      'routines': a list of routines.
      'token': nextPageToken for the last page, if present.
  """
  return (
      routines_api_client.routines()
      .list(
          projectId=reference.projectId,
          datasetId=reference.datasetId,
          maxResults=max_results,
          pageToken=page_token,
          filter=filter_expression,
      )
      .execute()
  )


def RoutineExists(
    routines_api_client: discovery.Resource,
    reference: 'bq_id_utils.ApiClientHelper.RoutineReference',
):
  """Returns true if the routine exists."""
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.RoutineReference,
      method='RoutineExists',
  )
  try:
    return (
        routines_api_client.routines()
        .get(
            projectId=reference.projectId,
            datasetId=reference.datasetId,
            routineId=reference.routineId,
        )
        .execute()
    )
  except bq_error.BigqueryNotFoundError:
    return False


def DeleteRoutine(
    routines_api_client: discovery.Resource,
    reference: 'bq_id_utils.ApiClientHelper.RoutineReference',
    ignore_not_found: Optional[bool] = False,
) -> None:
  """Deletes RoutineReference reference.

  Args:
    routines_api_client: the api client used to make the request.
    reference: the RoutineReference to delete.
    ignore_not_found: Whether to ignore "not found" errors.

  Raises:
    BigqueryTypeError: if reference is not a RoutineReference.
    bq_error.BigqueryNotFoundError: if reference does not exist and
      ignore_not_found is False.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.RoutineReference,
      method='DeleteRoutine',
  )
  try:
    routines_api_client.routines().delete(**dict(reference)).execute()
  except bq_error.BigqueryNotFoundError:
    if not ignore_not_found:
      raise


def SetRoutineIAMPolicy(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.RoutineReference,
    policy: str,
):
  """Sets IAM policy for the given routine resource.

  Arguments:
    apiclient: the apiclient used to make the request.
    reference: the RoutineReference for the routine resource.
    policy: The policy string in JSON format.

  Returns:
    The updated IAM policy attached to the given routine resource.

  Raises:
    BigqueryTypeError: if reference is not a RoutineReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.RoutineReference,
      method='SetRoutineIAMPolicy',
  )
  request = {'policy': policy}
  return (
      apiclient.routines()
      .setIamPolicy(body=request, resource=reference.path())
      .execute()
  )


def GetRoutineIAMPolicy(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.RoutineReference,
):
  """Gets IAM policy for the given routine resource.

  Arguments:
    apiclient: the apiclient used to make the request.
    reference: the RoutineReference for the routine resource.

  Returns:
    The IAM policy attached to the given routine resource.

  Raises:
    BigqueryTypeError: if reference is not a RoutineReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.RoutineReference,
      method='GetRoutineIAMPolicy',
  )
  return apiclient.routines().getIamPolicy(resource=reference.path()).execute()
