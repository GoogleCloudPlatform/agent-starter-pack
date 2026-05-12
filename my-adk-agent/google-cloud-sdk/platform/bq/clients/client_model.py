#!/usr/bin/env python
"""The BigQuery CLI model client library."""

from typing import Dict, List, Optional

from googleapiclient import discovery

from utils import bq_error
from utils import bq_id_utils


def list_models(
    model_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.DatasetReference,
    max_results: Optional[int],
    page_token: Optional[str],
):
  """Lists models for the given dataset reference.

  Arguments:
    model_client: The apiclient used to make the request.
    reference: Reference to the dataset.
    max_results: Number of results to return.
    page_token: Token to retrieve the next page of results.

  Returns:
    A dict that contains entries:
      'results': a list of models
      'token': nextPageToken for the last page, if present.
  """
  return (
      model_client.models()
      .list(
          projectId=reference.projectId,
          datasetId=reference.datasetId,
          maxResults=max_results,
          pageToken=page_token,
      )
      .execute()
  )


def model_exists(
    model_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ModelReference,
) -> bool:
  """Returns true if the model exists."""
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ModelReference,
      method='model_exists',
  )
  try:
    return (
        model_client.models()
        .get(
            projectId=reference.projectId,
            datasetId=reference.datasetId,
            modelId=reference.modelId,
        )
        .execute()
    )
  except bq_error.BigqueryNotFoundError:
    return False


def update_model(
    model_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ModelReference,
    description: Optional[str] = None,
    expiration: Optional[int] = None,
    labels_to_set: Optional[Dict[str, str]] = None,
    label_keys_to_remove: Optional[List[str]] = None,
    vertex_ai_model_id: Optional[str] = None,
    etag: Optional[str] = None,
):
  """Updates a Model.

  Args:
    model_client: The apiclient used to make the request.
    reference: the ModelReference to update.
    description: an optional description for model.
    expiration: optional expiration time in milliseconds since the epoch.
      Specifying 0 clears the expiration time for the model.
    labels_to_set: an optional dict of labels to set on this model.
    label_keys_to_remove: an optional list of label keys to remove from this
      model.
    vertex_ai_model_id: an optional string as Vertex AI model ID to register.
    etag: if set, checks that etag in the existing model matches.

  Raises:
    BigqueryTypeError: if reference is not a ModelReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ModelReference,
      method='update_model',
  )

  updated_model = {}
  if description is not None:
    updated_model['description'] = description
  if expiration is not None:
    updated_model['expirationTime'] = expiration or None
  if 'labels' not in updated_model:
    updated_model['labels'] = {}
  if labels_to_set:
    for label_key, label_value in labels_to_set.items():
      updated_model['labels'][label_key] = label_value
  if label_keys_to_remove:
    for label_key in label_keys_to_remove:
      updated_model['labels'][label_key] = None
  if vertex_ai_model_id is not None:
    updated_model['trainingRuns'] = [{'vertex_ai_model_id': vertex_ai_model_id}]

  request = model_client.models().patch(
      body=updated_model,
      projectId=reference.projectId,
      datasetId=reference.datasetId,
      modelId=reference.modelId,
  )

  # Perform a conditional update to protect against concurrent
  # modifications to this model. If there is a conflicting
  # change, this update will fail with a "Precondition failed"
  # error.
  if etag:
    request.headers['If-Match'] = etag if etag else updated_model['etag']
  request.execute()


def delete_model(
    model_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ModelReference,
    ignore_not_found: bool = False,
):
  """Deletes ModelReference reference.

  Args:
    model_client: The apiclient used to make the request.
    reference: the ModelReference to delete.
    ignore_not_found: Whether to ignore "not found" errors.

  Raises:
    BigqueryTypeError: if reference is not a ModelReference.
    bq_error.BigqueryNotFoundError: if reference does not exist and
      ignore_not_found is False.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ModelReference,
      method='delete_model',
  )
  try:
    model_client.models().delete(
        projectId=reference.projectId,
        datasetId=reference.datasetId,
        modelId=reference.modelId,
    ).execute()
  except bq_error.BigqueryNotFoundError:
    if not ignore_not_found:
      raise
