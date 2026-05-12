#!/usr/bin/env python
"""The BigQuery CLI table client library."""

from typing import Dict, List, Optional, cast

from googleapiclient import discovery

from clients import table_reader as bq_table_reader
from frontend import utils as bq_frontend_utils
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

_EXTERNAL_CATALOG_TABLE_OPTIONS_FIELD_NAME = 'externalCatalogTableOptions'


def get_table_schema(
    apiclient: discovery.Resource,
    table_dict: bq_id_utils.ApiClientHelper.TableReference,
):
  table_info = apiclient.tables().get(**table_dict).execute()
  return table_info.get('schema', {})


def insert_table_rows(
    insert_client: discovery.Resource,
    table_dict: bq_id_utils.ApiClientHelper.TableReference,
    inserts: List[Optional[bq_processor_utils.InsertEntry]],
    skip_invalid_rows: Optional[bool] = None,
    ignore_unknown_values: Optional[bool] = None,
    template_suffix: Optional[int] = None,
):
  """Insert rows into a table.

  Arguments:
    insert_client: The apiclient used to make the request.
    table_dict: table reference into which rows are to be inserted.
    inserts: array of InsertEntry tuples where insert_id can be None.
    skip_invalid_rows: Optional. Attempt to insert any valid rows, even if
      invalid rows are present.
    ignore_unknown_values: Optional. Ignore any values in a row that are not
      present in the schema.
    template_suffix: Optional. The suffix used to generate the template table's
      name.

  Returns:
    result of the operation.
  """

  def _encode_insert(insert):
    encoded = dict(json=insert.record)
    if insert.insert_id:
      encoded['insertId'] = insert.insert_id
    return encoded

  op = insert_client.tabledata().insertAll(
      body=dict(
          skipInvalidRows=skip_invalid_rows,
          ignoreUnknownValues=ignore_unknown_values,
          templateSuffix=template_suffix,
          rows=list(map(_encode_insert, inserts)),
      ),
      **table_dict,
  )
  return op.execute()


def read_schema_and_rows(
    apiclient: discovery.Resource,
    table_ref: bq_id_utils.ApiClientHelper.TableReference,
    start_row: Optional[int] = None,
    max_rows: Optional[int] = None,
    selected_fields: Optional[str] = None,
    max_rows_per_request: Optional[int] = None,
):
  """Convenience method to get the schema and rows from a table.

  Arguments:
    apiclient: The apiclient used to make the request.
    table_ref: table reference.
    start_row: first row to read.
    max_rows: number of rows to read.
    selected_fields: a subset of fields to return.
    max_rows_per_request: the maximum number of rows to read per request.

  Returns:
    A tuple where the first item is the list of fields and the
    second item a list of rows.

  Raises:
    ValueError: will be raised if start_row is not explicitly provided.
    ValueError: will be raised if max_rows is not explicitly provided.
  """
  if start_row is None:
    raise ValueError('start_row is required')
  if max_rows is None:
    raise ValueError('max_rows is required')
  table_reader = bq_table_reader.TableTableReader(
      apiclient, max_rows_per_request, table_ref
  )
  return table_reader.ReadSchemaAndRows(
      start_row,
      max_rows,
      selected_fields=selected_fields,
  )


def list_tables(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.DatasetReference,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
):
  """List the tables associated with this reference."""
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.DatasetReference,
      method='list_tables',
  )
  request = bq_processor_utils.PrepareListRequest(
      reference, max_results, page_token
  )
  result = apiclient.tables().list(**request).execute()
  results = result.get('tables', [])
  if max_results is not None:
    while 'nextPageToken' in result and len(results) < max_results:
      request['maxResults'] = max_results - len(results)
      request['pageToken'] = result['nextPageToken']
      result = apiclient.tables().list(**request).execute()
      results.extend(result.get('tables', []))
  return results


def get_table_iam_policy(
    iampolicy_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
):
  """Gets IAM policy for the given table resource.

  Arguments:
    iampolicy_client: The apiclient used to make the request.
    reference: the TableReference for the table resource.

  Returns:
    The IAM policy attached to the given table resource.

  Raises:
    BigqueryTypeError: if reference is not a TableReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='get_table_iam_policy',
  )
  formatted_resource = 'projects/%s/datasets/%s/tables/%s' % (
      reference.projectId,
      reference.datasetId,
      reference.tableId,
  )
  return (
      iampolicy_client.tables()
      .getIamPolicy(resource=formatted_resource)
      .execute()
  )


def set_table_iam_policy(
    iampolicy_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
    policy,
):
  """Sets IAM policy for the given table resource.

  Arguments:
    iampolicy_client: The apiclient used to make the request.
    reference: the TableReference for the table resource.
    policy: The policy string in JSON format.

  Returns:
    The updated IAM policy attached to the given table resource.

  Raises:
    BigqueryTypeError: if reference is not a TableReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='set_table_iam_policy',
  )
  formatted_resource = 'projects/%s/datasets/%s/tables/%s' % (
      reference.projectId,
      reference.datasetId,
      reference.tableId,
  )
  request = {'policy': policy}
  return (
      iampolicy_client.tables()
      .setIamPolicy(body=request, resource=formatted_resource)
      .execute()
  )


def get_table_region(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
) -> Optional[str]:
  """Returns the region of a table as a string."""
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='get_table_region',
  )
  try:
    return apiclient.tables().get(**dict(reference)).execute()['location']
  except bq_error.BigqueryNotFoundError:
    return None


def table_exists(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
):
  """Returns true if the table exists."""
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='table_exists',
  )
  try:
    return apiclient.tables().get(**dict(reference)).execute()
  except bq_error.BigqueryNotFoundError:
    return False


def create_table(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
    ignore_existing: bool = False,
    schema: Optional[str] = None,
    description: Optional[str] = None,
    display_name: Optional[str] = None,
    expiration: Optional[int] = None,
    view_query: Optional[str] = None,
    materialized_view_query: Optional[str] = None,
    enable_refresh: Optional[bool] = None,
    refresh_interval_ms: Optional[int] = None,
    max_staleness: Optional[str] = None,
    external_data_config=None,
    biglake_config=None,
    external_catalog_table_options=None,
    view_udf_resources=None,
    use_legacy_sql: Optional[bool] = None,
    labels: Optional[Dict[str, str]] = None,
    time_partitioning=None,
    clustering: Optional[Dict[str, List[str]]] = None,
    range_partitioning=None,
    require_partition_filter: Optional[bool] = None,
    destination_kms_key: Optional[str] = None,
    location: Optional[str] = None,
    table_constraints: Optional[str] = None,
    resource_tags: Optional[Dict[str, str]] = None,
):
  """Create a table corresponding to TableReference.

  Args:
    apiclient: The apiclient used to make the request.
    reference: the TableReference to create.
    ignore_existing: (boolean, default False) If False, raise an exception if
      the dataset already exists.
    schema: an optional schema for tables.
    description: an optional description for tables or views.
    display_name: an optional friendly name for the table.
    expiration: optional expiration time in milliseconds since the epoch for
      tables or views.
    view_query: an optional Sql query for views.
    materialized_view_query: an optional standard SQL query for materialized
      views.
    enable_refresh: for materialized views, an optional toggle to enable /
      disable automatic refresh when the base table is updated.
    refresh_interval_ms: for materialized views, an optional maximum frequency
      for automatic refreshes.
    max_staleness: INTERVAL value that determines the maximum staleness allowed
      when querying a materialized view or an external table. By default no
      staleness is allowed.
    external_data_config: defines a set of external resources used to create an
      external table. For example, a BigQuery table backed by CSV files in GCS.
    biglake_config: specifies the configuration of a BigLake managed table.
    external_catalog_table_options: Specifies the configuration of an external
      catalog table.
    view_udf_resources: optional UDF resources used in a view.
    use_legacy_sql: The choice of using Legacy SQL for the query is optional. If
      not specified, the server will automatically determine the dialect based
      on query information, such as dialect prefixes. If no prefixes are found,
      it will default to Legacy SQL.
    labels: an optional dict of labels to set on the table.
    time_partitioning: if set, enables time based partitioning on the table and
      configures the partitioning.
    clustering: if set, enables and configures clustering on the table.
    range_partitioning: if set, enables range partitioning on the table and
      configures the partitioning.
    require_partition_filter: if set, partition filter is required for queiries
      over this table.
    destination_kms_key: User specified KMS key for encryption.
    location: an optional location for which to create tables or views.
    table_constraints: an optional primary key and foreign key configuration for
      the table.
    resource_tags: an optional dict of tags to attach to the table.

  Raises:
    BigqueryTypeError: if reference is not a TableReference.
    BigqueryDuplicateError: if reference exists and ignore_existing
      is False.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='create_table',
  )

  try:
    body = bq_processor_utils.ConstructObjectInfo(reference)
    if schema is not None:
      body['schema'] = {'fields': schema}
    if display_name is not None:
      body['friendlyName'] = display_name
    if description is not None:
      body['description'] = description
    if expiration is not None:
      body['expirationTime'] = expiration
    if view_query is not None:
      view_args = {'query': view_query}
      if view_udf_resources is not None:
        view_args['userDefinedFunctionResources'] = view_udf_resources
      body['view'] = view_args
      if use_legacy_sql is not None:
        view_args['useLegacySql'] = use_legacy_sql
    if materialized_view_query is not None:
      materialized_view_args = {'query': materialized_view_query}
      if enable_refresh is not None:
        materialized_view_args['enableRefresh'] = enable_refresh
      if refresh_interval_ms is not None:
        materialized_view_args['refreshIntervalMs'] = refresh_interval_ms
      body['materializedView'] = materialized_view_args
    if external_data_config is not None:
      if max_staleness is not None:
        body['maxStaleness'] = max_staleness
      body['externalDataConfiguration'] = external_data_config
    if biglake_config is not None:
      body['biglakeConfiguration'] = biglake_config
    if external_catalog_table_options is not None:
      body['externalCatalogTableOptions'] = bq_frontend_utils.GetJson(
          external_catalog_table_options
      )
    if labels is not None:
      body['labels'] = labels
    if time_partitioning is not None:
      body['timePartitioning'] = time_partitioning
    if clustering is not None:
      body['clustering'] = clustering
    if range_partitioning is not None:
      body['rangePartitioning'] = range_partitioning
    if require_partition_filter is not None:
      body['requirePartitionFilter'] = require_partition_filter
    if destination_kms_key is not None:
      body['encryptionConfiguration'] = {'kmsKeyName': destination_kms_key}
    if location is not None:
      body['location'] = location
    if table_constraints is not None:
      body['table_constraints'] = table_constraints
    if resource_tags is not None:
      body['resourceTags'] = resource_tags
    _execute_insert_table_request(apiclient, reference, body)
  except bq_error.BigqueryDuplicateError:
    if not ignore_existing:
      raise


def update_table(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
    schema=None,
    description: Optional[str] = None,
    display_name: Optional[str] = None,
    expiration: Optional[int] = None,
    view_query: Optional[str] = None,
    materialized_view_query: Optional[str] = None,
    enable_refresh: Optional[bool] = None,
    refresh_interval_ms: Optional[int] = None,
    max_staleness: Optional[str] = None,
    external_data_config=None,
    external_catalog_table_options=None,
    view_udf_resources=None,
    use_legacy_sql: Optional[bool] = None,
    labels_to_set: Optional[Dict[str, str]] = None,
    label_keys_to_remove: Optional[List[str]] = None,
    time_partitioning=None,
    range_partitioning=None,
    clustering: Optional[Dict[str, List[str]]] = None,
    require_partition_filter: Optional[bool] = None,
    etag: Optional[str] = None,
    encryption_configuration=None,
    location: Optional[str] = None,
    autodetect_schema: bool = False,
    table_constraints=None,
    tags_to_attach: Optional[Dict[str, str]] = None,
    tags_to_remove: Optional[List[str]] = None,
    clear_all_tags: bool = False,
):
  """Updates a table.

  Args:
    apiclient: The apiclient used to make the request.
    reference: the TableReference to update.
    schema: an optional schema for tables.
    description: an optional description for tables or views.
    display_name: an optional friendly name for the table.
    expiration: optional expiration time in milliseconds since the epoch for
      tables or views. Specifying 0 removes expiration time.
    view_query: an optional Sql query to update a view.
    materialized_view_query: an optional Standard SQL query for materialized
      views.
    enable_refresh: for materialized views, an optional toggle to enable /
      disable automatic refresh when the base table is updated.
    refresh_interval_ms: for materialized views, an optional maximum frequency
      for automatic refreshes.
    max_staleness: INTERVAL value that determines the maximum staleness allowed
      when querying a materialized view or an external table. By default no
      staleness is allowed.
    external_data_config: defines a set of external resources used to create an
      external table. For example, a BigQuery table backed by CSV files in GCS.
    external_catalog_table_options: Specifies the configuration of an external
      catalog table.
    view_udf_resources: optional UDF resources used in a view.
    use_legacy_sql: The choice of using Legacy SQL for the query is optional. If
      not specified, the server will automatically determine the dialect based
      on query information, such as dialect prefixes. If no prefixes are found,
      it will default to Legacy SQL.
    labels_to_set: an optional dict of labels to set on this table.
    label_keys_to_remove: an optional list of label keys to remove from this
      table.
    time_partitioning: if set, enables time based partitioning on the table and
      configures the partitioning.
    range_partitioning: if set, enables range partitioning on the table and
      configures the partitioning.
    clustering: if set, enables clustering on the table and configures the
      clustering spec.
    require_partition_filter: if set, partition filter is required for queiries
      over this table.
    etag: if set, checks that etag in the existing table matches.
    encryption_configuration: Updates the encryption configuration.
    location: an optional location for which to update tables or views.
    autodetect_schema: an optional flag to perform autodetect of file schema.
    table_constraints: an optional primary key and foreign key configuration for
      the table.
    tags_to_attach: an optional dict of tags to attach to the table
    tags_to_remove: an optional list of tag keys to remove from the table
    clear_all_tags: if set, clears all the tags attached to the table

  Raises:
    BigqueryTypeError: if reference is not a TableReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='update_table',
  )

  existing_table = {}
  if clear_all_tags:
    # getting existing table. This is required to clear all tags attached to
    # a table. Adding this at the start of the method as this can also be
    # used for other scenarios
    existing_table = _execute_get_table_request(
        apiclient=apiclient, reference=reference
    )
  table = bq_processor_utils.ConstructObjectInfo(reference)
  maybe_skip_schema = False
  if schema is not None:
    table['schema'] = {'fields': schema}
  elif not maybe_skip_schema:
    table['schema'] = None

  if encryption_configuration is not None:
    table['encryptionConfiguration'] = encryption_configuration
  if display_name is not None:
    table['friendlyName'] = display_name
  if description is not None:
    table['description'] = description
  if expiration is not None:
    if expiration == 0:
      table['expirationTime'] = None
    else:
      table['expirationTime'] = expiration
  if view_query is not None:
    view_args = {'query': view_query}
    if view_udf_resources is not None:
      view_args['userDefinedFunctionResources'] = view_udf_resources
    if use_legacy_sql is not None:
      view_args['useLegacySql'] = use_legacy_sql
    table['view'] = view_args
  materialized_view_args = {}
  if materialized_view_query is not None:
    materialized_view_args['query'] = materialized_view_query
  if enable_refresh is not None:
    materialized_view_args['enableRefresh'] = enable_refresh
  if refresh_interval_ms is not None:
    materialized_view_args['refreshIntervalMs'] = refresh_interval_ms
  if materialized_view_args:
    table['materializedView'] = materialized_view_args

  if external_data_config is not None:
    table['externalDataConfiguration'] = external_data_config
    if max_staleness is not None:
      table['maxStaleness'] = max_staleness
  if 'labels' not in table:
    table['labels'] = {}
  table_labels = cast(Dict[str, Optional[str]], table['labels'])
  if table_labels is None:
    raise ValueError('Missing labels in table.')
  if labels_to_set:
    for label_key, label_value in labels_to_set.items():
      table_labels[label_key] = label_value
  if label_keys_to_remove:
    for label_key in label_keys_to_remove:
      table_labels[label_key] = None
  if time_partitioning is not None:
    table['timePartitioning'] = time_partitioning
  if range_partitioning is not None:
    table['rangePartitioning'] = range_partitioning
  if clustering is not None:
    if clustering == {}:  # pylint: disable=g-explicit-bool-comparison
      table['clustering'] = None
    else:
      table['clustering'] = clustering
  if require_partition_filter is not None:
    table['requirePartitionFilter'] = require_partition_filter
  if location is not None:
    table['location'] = location
  if table_constraints is not None:
    table['table_constraints'] = table_constraints
  resource_tags = {}
  if clear_all_tags and 'resourceTags' in existing_table:
    for tag in existing_table['resourceTags']:
      resource_tags[tag] = None
  else:
    for tag in tags_to_remove or []:
      resource_tags[tag] = None
  for tag in tags_to_attach or {}:
    resource_tags[tag] = tags_to_attach[tag]
  # resourceTags is used to add a new tag binding, update value of existing
  # tag and also to remove a tag binding
  # check go/bq-table-tags-api for details
  table['resourceTags'] = resource_tags

  if external_catalog_table_options is not None:
    existing_table = _execute_get_table_request(
        apiclient=apiclient, reference=reference
    )
    existing_table.setdefault(_EXTERNAL_CATALOG_TABLE_OPTIONS_FIELD_NAME, {})
    table[_EXTERNAL_CATALOG_TABLE_OPTIONS_FIELD_NAME] = (
        bq_frontend_utils.UpdateExternalCatalogTableOptions(
            existing_table[_EXTERNAL_CATALOG_TABLE_OPTIONS_FIELD_NAME],
            external_catalog_table_options,
        )
    )
  _execute_patch_table_request(
      apiclient=apiclient,
      reference=reference,
      table=table,
      autodetect_schema=autodetect_schema,
      etag=etag,
  )


def _execute_get_table_request(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
):
  return apiclient.tables().get(**dict(reference)).execute()


def _execute_patch_table_request(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
    table,
    autodetect_schema: bool = False,
    etag: Optional[str] = None,
):
  """Executes request to patch table.

  Args:
    apiclient: The apiclient used to make the request.
    reference: the TableReference to patch.
    table: the body of request
    autodetect_schema: an optional flag to perform autodetect of file schema.
    etag: if set, checks that etag in the existing table matches.
  """
  request = apiclient.tables().patch(
      autodetect_schema=autodetect_schema, body=table, **dict(reference)
  )

  # Perform a conditional update to protect against concurrent
  # modifications to this table. If there is a conflicting
  # change, this update will fail with a "Precondition failed"
  # error.
  if etag:
    request.headers['If-Match'] = etag if etag else table['etag']
  request.execute()


def _execute_insert_table_request(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
    body,
):
  apiclient.tables().insert(
      body=body, **dict(reference.GetDatasetReference())
  ).execute()


def delete_table(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TableReference,
    ignore_not_found: bool = False,
):
  """Deletes TableReference reference.

  Args:
    apiclient: The apiclient used to make the request.
    reference: the TableReference to delete.
    ignore_not_found: Whether to ignore "not found" errors.

  Raises:
    BigqueryTypeError: if reference is not a TableReference.
    bq_error.BigqueryNotFoundError: if reference does not exist and
      ignore_not_found is False.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='delete_table',
  )
  try:
    apiclient.tables().delete(**dict(reference)).execute()
  except bq_error.BigqueryNotFoundError:
    if not ignore_not_found:
      raise
