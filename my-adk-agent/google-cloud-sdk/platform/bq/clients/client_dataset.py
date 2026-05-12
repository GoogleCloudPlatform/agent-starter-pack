#!/usr/bin/env python
"""The BigQuery CLI dataset client library."""

import datetime
from typing import Dict, List, NamedTuple, Optional
from googleapiclient import discovery
from clients import utils as bq_client_utils
from frontend import utils as frontend_utils
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

EXTERNAL_CATALOG_DATASET_OPTIONS_FIELD_NAME = 'externalCatalogDatasetOptions'


def GetDataset(apiclient: discovery.Resource, reference, dataset_view=None):
  """Get dataset with dataset_view parameter."""
  request = dict(reference)
  request['accessPolicyVersion'] = (
      bq_client_utils.MAX_SUPPORTED_IAM_POLICY_VERSION
  )
  if dataset_view is not None:
    request['datasetView'] = dataset_view
  return apiclient.datasets().get(**request).execute()


def ListDatasets(
    apiclient: discovery.Resource,
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    reference: Optional[bq_id_utils.ApiClientHelper.ProjectReference] = None,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    list_all: Optional[bool] = None,
    filter_expression: Optional[str] = None,
):
  """List the datasets associated with this reference."""
  return ListDatasetsWithTokenAndUnreachable(
      apiclient,
      id_fallbacks,
      reference,
      max_results,
      page_token,
      list_all,
      filter_expression,
  )['datasets']


def ListDatasetsWithTokenAndUnreachable(
    apiclient: discovery.Resource,
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    reference: Optional[bq_id_utils.ApiClientHelper.ProjectReference] = None,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    list_all: Optional[bool] = None,
    filter_expression: Optional[str] = None,
):
  """List the datasets associated with this reference."""
  reference = bq_client_utils.NormalizeProjectReference(
      id_fallbacks=id_fallbacks, reference=reference
  )
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ProjectReference,
      method='ListDatasets',
  )
  request = bq_processor_utils.PrepareListRequest(
      reference, max_results, page_token, filter_expression
  )
  if list_all is not None:
    request['all'] = list_all
  result = apiclient.datasets().list(**request).execute()
  dataset_list = result.get('datasets', [])
  unreachable_set = set(result.get('unreachable', []))
  next_token = result.get('nextPageToken', None)
  if max_results is not None:
    while 'nextPageToken' in result and len(dataset_list) < max_results:
      request['maxResults'] = max_results - len(dataset_list)
      request['pageToken'] = result['nextPageToken']
      result = apiclient.datasets().list(**request).execute()
      dataset_list.extend(result.get('datasets', []))
      unreachable_set.update(result.get('unreachable', []))
      next_token = result.get('nextPageToken', None)
  response = dict(datasets=dataset_list)
  if next_token:
    response['token'] = next_token
  if unreachable_set:
    response['unreachable'] = list(unreachable_set)
  return response


def GetDatasetIAMPolicy(apiclient, reference):
  """Gets IAM policy for the given dataset resource.

  Arguments:
    apiclient: the apiclient used to make the request.
    reference: the DatasetReference for the dataset resource.

  Returns:
    The IAM policy attached to the given dataset resource.

  Raises:
    BigqueryTypeError: if reference is not a DatasetReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='GetDatasetIAMPolicy',
  )
  formatted_resource = 'projects/%s/datasets/%s' % (
      reference.projectId,
      reference.datasetId,
  )
  body = {
      'options': {
          'requestedPolicyVersion': (
              bq_client_utils.MAX_SUPPORTED_IAM_POLICY_VERSION
          )
      }
  }
  return (
      apiclient.datasets()
      .getIamPolicy(
          resource=formatted_resource,
          body=body,
      )
      .execute()
  )


def SetDatasetIAMPolicy(apiclient: discovery.Resource, reference, policy):
  """Sets IAM policy for the given dataset resource.

  Arguments:
    apiclient: the apiclient used to make the request.
    reference: the DatasetReference for the dataset resource.
    policy: The policy string in JSON format.

  Returns:
    The updated IAM policy attached to the given dataset resource.

  Raises:
    BigqueryTypeError: if reference is not a DatasetReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='SetDatasetIAMPolicy',
  )
  formatted_resource = 'projects/%s/datasets/%s' % (
      reference.projectId,
      reference.datasetId,
  )
  request = {'policy': policy}
  return (
      apiclient.datasets()
      .setIamPolicy(body=request, resource=formatted_resource)
      .execute()
  )


def DatasetExists(
    apiclient: discovery.Resource,
    reference: 'bq_id_utils.ApiClientHelper.DatasetReference',
) -> bool:
  """Returns true if a dataset exists."""
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='DatasetExists',
  )
  try:
    apiclient.datasets().get(**dict(reference)).execute()
    return True
  except bq_error.BigqueryNotFoundError:
    return False


def GetDatasetRegion(
    apiclient: discovery.Resource,
    reference: 'bq_id_utils.ApiClientHelper.DatasetReference',
) -> Optional[str]:
  """Returns the region of a dataset as a string."""
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='GetDatasetRegion',
  )
  try:
    return apiclient.datasets().get(**dict(reference)).execute()['location']
  except bq_error.BigqueryNotFoundError:
    return None


# TODO(b/191712821): add tags modification here. For the Preview Tags are not
# modifiable using BigQuery UI/Cli, only using ResourceManager.
def CreateDataset(
    apiclient: discovery.Resource,
    reference,
    ignore_existing=False,
    description=None,
    display_name=None,
    acl=None,
    default_table_expiration_ms=None,
    default_partition_expiration_ms=None,
    data_location=None,
    labels=None,
    default_kms_key=None,
    source_dataset_reference=None,
    external_source=None,
    connection_id=None,
    external_catalog_dataset_options=None,
    max_time_travel_hours=None,
    storage_billing_model=None,
    resource_tags=None,
):
  """Create a dataset corresponding to DatasetReference.

  Args:
    apiclient: The apiclient used to make the request.
    reference: The DatasetReference to create.
    ignore_existing: (boolean, default False) If False, raise an exception if
      the dataset already exists.
    description: An optional dataset description.
    display_name: An optional friendly name for the dataset.
    acl: An optional ACL for the dataset, as a list of dicts.
    default_table_expiration_ms: Default expiration time to apply to new tables
      in this dataset.
    default_partition_expiration_ms: Default partition expiration time to apply
      to new partitioned tables in this dataset.
    data_location: Location where the data in this dataset should be stored.
      Must be either 'EU' or 'US'. If specified, the project that owns the
      dataset must be enabled for data location.
    labels: An optional dict of labels.
    default_kms_key: An optional kms dey that will apply to all newly created
      tables in the dataset, if no explicit key is supplied in the creating
      request.
    source_dataset_reference: An optional ApiClientHelper.DatasetReference that
      will be the source of this linked dataset. #
    external_source: External source that backs this dataset.
    connection_id: Connection used for accessing the external_source.
    external_catalog_dataset_options: An optional JSON string or file path
      containing the external catalog dataset options to create.
    max_time_travel_hours: Optional. Define the max time travel in hours. The
      value can be from 48 to 168 hours (2 to 7 days). The default value is 168
      hours if this is not set.
    storage_billing_model: Optional. Sets the storage billing model for the
      dataset.
    resource_tags: An optional dict of tags to attach to the dataset.

  Raises:
    BigqueryTypeError: If reference is not an ApiClientHelper.DatasetReference
      or if source_dataset_reference is provided but is not an
      bq_id_utils.ApiClientHelper.DatasetReference.
      or if both external_dataset_reference and source_dataset_reference
      are provided or if not all required arguments for external database is
      provided.
    BigqueryDuplicateError: if reference exists and ignore_existing
        is False.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='CreateDataset',
  )

  body = bq_processor_utils.ConstructObjectInfo(reference)
  if display_name is not None:
    body['friendlyName'] = display_name
  if description is not None:
    body['description'] = description
  if acl is not None:
    body['access'] = acl
  if default_table_expiration_ms is not None:
    body['defaultTableExpirationMs'] = default_table_expiration_ms
  if default_partition_expiration_ms is not None:
    body['defaultPartitionExpirationMs'] = default_partition_expiration_ms
  if default_kms_key is not None:
    body['defaultEncryptionConfiguration'] = {'kmsKeyName': default_kms_key}
  if data_location is not None:
    body['location'] = data_location
  if labels:
    body['labels'] = {}
    for label_key, label_value in labels.items():
      body['labels'][label_key] = label_value
  if source_dataset_reference is not None:
    bq_id_utils.typecheck(
        source_dataset_reference,
        bq_id_utils.ApiClientHelper.DatasetReference,
        method='CreateDataset',
    )
    body['linkedDatasetSource'] = {
        'sourceDataset': bq_processor_utils.ConstructObjectInfo(
            source_dataset_reference
        )['datasetReference']
    }
  # externalDatasetReference can only be specified in case of externals
  # datasets. This option cannot be used in case of regular dataset or linked
  # datasets.
  # So we only set this if an external_source is specified.
  if external_source:
    body['externalDatasetReference'] = {
        'externalSource': external_source,
        'connection': connection_id,
    }
  if external_catalog_dataset_options is not None:
    body[EXTERNAL_CATALOG_DATASET_OPTIONS_FIELD_NAME] = frontend_utils.GetJson(
        external_catalog_dataset_options
    )
  if max_time_travel_hours is not None:
    body['maxTimeTravelHours'] = max_time_travel_hours
  if storage_billing_model is not None:
    body['storageBillingModel'] = storage_billing_model
  if resource_tags is not None:
    body['resourceTags'] = resource_tags

  args = dict(reference.GetProjectReference())
  args['accessPolicyVersion'] = bq_client_utils.MAX_SUPPORTED_IAM_POLICY_VERSION
  try:
    apiclient.datasets().insert(body=body, **args).execute()
  except bq_error.BigqueryDuplicateError:
    if not ignore_existing:
      raise


def UpdateDataset(
    apiclient: discovery.Resource,
    reference: 'bq_id_utils.ApiClientHelper.DatasetReference',
    description: Optional[str] = None,
    display_name: Optional[str] = None,
    acl=None,
    default_table_expiration_ms=None,
    default_partition_expiration_ms=None,
    labels_to_set=None,
    label_keys_to_remove=None,
    etag=None,
    default_kms_key=None,
    max_time_travel_hours=None,
    storage_billing_model=None,
    tags_to_attach: Optional[Dict[str, str]] = None,
    tags_to_remove: Optional[List[str]] = None,
    clear_all_tags: Optional[bool] = False,
    external_catalog_dataset_options: Optional[str] = None,
    update_mode: Optional[bq_client_utils.UpdateMode] = None,
):
  """Updates a dataset.

  Args:
    apiclient: The apiclient used to make the request.
    reference: The DatasetReference to update.
    description: An optional dataset description.
    display_name: An optional friendly name for the dataset.
    acl: An optional ACL for the dataset, as a list of dicts.
    default_table_expiration_ms: Optional number of milliseconds for the default
      expiration duration for new tables created in this dataset.
    default_partition_expiration_ms: Optional number of milliseconds for the
      default partition expiration duration for new partitioned tables created
      in this dataset.
    labels_to_set: An optional dict of labels to set on this dataset.
    label_keys_to_remove: An optional list of label keys to remove from this
      dataset.
    etag: If set, checks that etag in the existing dataset matches.
    default_kms_key: An optional kms dey that will apply to all newly created
      tables in the dataset, if no explicit key is supplied in the creating
      request.
    max_time_travel_hours: Optional. Define the max time travel in hours. The
      value can be from 48 to 168 hours (2 to 7 days). The default value is 168
      hours if this is not set.
    storage_billing_model: Optional. Sets the storage billing model for the
      dataset.
    tags_to_attach: An optional dict of tags to attach to the dataset
    tags_to_remove: An optional list of tag keys to remove from the dataset
    clear_all_tags: If set, clears all the tags attached to the dataset
    external_catalog_dataset_options: An optional JSON string or file path
      containing the external catalog dataset options to update.
    update_mode: An optional flag indicating which datasets fields to update,
      either metadata fields only, ACL fields only, or both metadata and ACL
      fields.

  Raises:
    BigqueryTypeError: If reference is not a DatasetReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='UpdateDataset',
  )

  # Get the existing dataset and associated ETag.
  dataset = _ExecuteGetDatasetRequest(apiclient, reference, etag)

  # Merge in the changes.
  if display_name is not None:
    dataset['friendlyName'] = display_name
  if description is not None:
    dataset['description'] = description
  if acl is not None:
    dataset['access'] = acl
  if default_table_expiration_ms is not None:
    dataset['defaultTableExpirationMs'] = default_table_expiration_ms
  if default_partition_expiration_ms is not None:
    if default_partition_expiration_ms == 0:
      dataset['defaultPartitionExpirationMs'] = None
    else:
      dataset['defaultPartitionExpirationMs'] = default_partition_expiration_ms
  if default_kms_key is not None:
    dataset['defaultEncryptionConfiguration'] = {'kmsKeyName': default_kms_key}
  if 'labels' not in dataset:
    dataset['labels'] = {}
  if labels_to_set:
    for label_key, label_value in labels_to_set.items():
      dataset['labels'][label_key] = label_value
  if label_keys_to_remove:
    for label_key in label_keys_to_remove:
      dataset['labels'][label_key] = None
  if max_time_travel_hours is not None:
    dataset['maxTimeTravelHours'] = max_time_travel_hours
  if storage_billing_model is not None:
    dataset['storageBillingModel'] = storage_billing_model
  resource_tags = {}
  if clear_all_tags and 'resourceTags' in dataset:
    for tag in dataset['resourceTags']:
      resource_tags[tag] = None
  else:
    for tag in tags_to_remove or []:
      resource_tags[tag] = None
  for tag in tags_to_attach or {}:
    resource_tags[tag] = tags_to_attach[tag]
  # resourceTags is used to add a new tag binding, update value of existing
  # tag and also to remove a tag binding
  dataset['resourceTags'] = resource_tags

  if external_catalog_dataset_options is not None:
    dataset.setdefault(EXTERNAL_CATALOG_DATASET_OPTIONS_FIELD_NAME, {})
    current_options = dataset[EXTERNAL_CATALOG_DATASET_OPTIONS_FIELD_NAME]
    dataset[EXTERNAL_CATALOG_DATASET_OPTIONS_FIELD_NAME] = (
        frontend_utils.UpdateExternalCatalogDatasetOptions(
            current_options, external_catalog_dataset_options
        )
    )

  _ExecutePatchDatasetRequest(
      apiclient,
      reference,
      dataset,
      etag,
      update_mode,
  )


def _ExecuteGetDatasetRequest(
    apiclient: discovery.Resource,
    reference,
    etag: Optional[str] = None,
):
  """Executes request to get dataset.

  Args:
    apiclient: the apiclient used to make the request.
    reference: the DatasetReference to get.
    etag: if set, checks that etag in the existing dataset matches.

  Returns:
  The result of executing the request, if it succeeds.
  """
  args = dict(reference)
  args['accessPolicyVersion'] = bq_client_utils.MAX_SUPPORTED_IAM_POLICY_VERSION
  get_request = apiclient.datasets().get(**args)
  if etag:
    get_request.headers['If-Match'] = etag
  dataset = get_request.execute()
  return dataset


def _ExecutePatchDatasetRequest(
    apiclient: discovery.Resource,
    reference,
    dataset,
    etag: Optional[str] = None,
    update_mode: Optional[bq_client_utils.UpdateMode] = None,
):
  """Executes request to patch dataset.

  Args:
    apiclient: the apiclient used to make the request.
    reference: the DatasetReference to patch.
    dataset: the body of request
    etag: if set, checks that etag in the existing dataset matches.
    update_mode: a flag indicating which datasets fields to update.
  """
  parameters = dict(reference)
  parameters['accessPolicyVersion'] = (
      bq_client_utils.MAX_SUPPORTED_IAM_POLICY_VERSION
  )
  if update_mode is not None:
    parameters['updateMode'] = update_mode.value

  request = apiclient.datasets().patch(body=dataset, **parameters)

  # Perform a conditional update to protect against concurrent
  # modifications to this dataset.  By placing the ETag returned in
  # the get operation into the If-Match header, the API server will
  # make sure the dataset hasn't changed.  If there is a conflicting
  # change, this update will fail with a "Precondition failed"
  # error.
  if etag or dataset['etag']:
    request.headers['If-Match'] = etag if etag else dataset['etag']
  request.execute()


def DeleteDataset(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.DatasetReference,
    ignore_not_found: bool = False,
    delete_contents: Optional[bool] = None,
) -> None:
  """Deletes DatasetReference reference.

  Args:
    apiclient: the api client to make the request with.
    reference: the DatasetReference to delete.
    ignore_not_found: Whether to ignore "not found" errors.
    delete_contents: [Boolean] Whether to delete the contents of non-empty
      datasets. If not specified and the dataset has tables in it, the delete
      will fail. If not specified, the server default applies.

  Raises:
    BigqueryTypeError: if reference is not a DatasetReference.
    bq_error.BigqueryNotFoundError: if reference does not exist and
      ignore_not_found is False.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='DeleteDataset',
  )

  args = dict(reference)

  if delete_contents is not None:
    args['deleteContents'] = delete_contents
  try:
    apiclient.datasets().delete(**args).execute()
  except bq_error.BigqueryNotFoundError:
    if not ignore_not_found:
      raise


def UndeleteDataset(
    apiclient: discovery.Resource,
    dataset_reference: bq_id_utils.ApiClientHelper.DatasetReference,
    timestamp: Optional[datetime.datetime] = None,
) -> bool:
  """Undeletes a dataset.

  Args:
    apiclient: The api client to make the request with.
    dataset_reference: [Type:
      bq_id_utils.ApiClientHelper.DatasetReference]DatasetReference of the
      dataset to be undeleted
    timestamp: [Type: Optional[datetime.datetime]]Timestamp for which dataset
      version is to be undeleted

  Returns:
    bool: The job description, or None for ignored errors.

  Raises:
    BigqueryDuplicateError: when the dataset to be undeleted already exists.
  """
  try:
    args = dict(dataset_reference)
    if timestamp:
      args['body'] = {
          'deletionTime': frontend_utils.FormatRfc3339(timestamp).replace(
              '+00:00', ''
          )
      }
    return apiclient.datasets().undelete(**args).execute()

  except bq_error.BigqueryDuplicateError as e:
    raise e
