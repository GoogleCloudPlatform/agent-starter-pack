#!/usr/bin/env python
"""The BigQuery CLI job client library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Union
import uuid

# To configure apiclient logging.
from absl import flags
from googleapiclient import http as http_request

import bq_flags
from clients import bigquery_client
from clients import table_reader as bq_table_reader
from clients import utils as bq_client_utils
from clients import wait_printer
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils


def ReadSchemaAndJobRows(
    bqclient: bigquery_client.BigqueryClient,
    job_dict: Dict[str, str],  # Can be stricter.
    start_row: Optional[int],
    max_rows: Optional[int],
    result_first_page=None,
):
  """Convenience method to get the schema and rows from job query result.

  Arguments:
    bqclient: A BigqueryClient to get state and request clients from.
    job_dict: job reference dictionary.
    start_row: first row to read.
    max_rows: number of rows to read.
    result_first_page: the first page of the result of a query job.

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
  if not job_dict:
    job_ref: bq_id_utils.ApiClientHelper.JobReference = None
  else:
    job_ref = bq_id_utils.ApiClientHelper.JobReference.Create(**job_dict)
  if flags.FLAGS.jobs_query_use_results_from_response and result_first_page:
    reader = bq_table_reader.QueryTableReader(
        bqclient.apiclient,
        bqclient.max_rows_per_request,
        job_ref,
        result_first_page,
    )
  else:
    reader = bq_table_reader.JobTableReader(
        bqclient.apiclient, bqclient.max_rows_per_request, job_ref
    )
  return reader.ReadSchemaAndRows(
      start_row, max_rows,
  )


def ListJobRefs(bqclient: bigquery_client.BigqueryClient, **kwds):
  return list(
      map(  # pylint: disable=g-long-lambda
          bq_processor_utils.ConstructObjectReference,
          ListJobs(bqclient, **kwds),
      )
  )


def ListJobs(
    bqclient: bigquery_client.BigqueryClient,
    reference: Optional[bq_id_utils.ApiClientHelper.ProjectReference] = None,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    state_filter: Optional[Union[List[str], str]] = None,  # Actually an enum.
    min_creation_time: Optional[str] = None,
    max_creation_time: Optional[str] = None,
    all_users: Optional[bool] = None,
    parent_job_id: Optional[str] = None,
):
  # pylint: disable=g-doc-args
  """Return a list of jobs.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    reference: The ProjectReference to list jobs for.
    max_results: The maximum number of jobs to return.
    page_token: Current page token (optional).
    state_filter: A single state filter or a list of filters to apply. If not
      specified, no filtering is applied.
    min_creation_time: Timestamp in milliseconds. Only return jobs created after
      or at this timestamp.
    max_creation_time: Timestamp in milliseconds. Only return jobs created
      before or at this timestamp.
    all_users: Whether to list jobs for all users of the project. Requesting
      user must be an owner of the project to list all jobs.
    parent_job_id: Retrieve only child jobs belonging to this parent; None to
      retrieve top-level jobs.

  Returns:
    A list of jobs.
  """
  return ListJobsWithTokenAndUnreachable(
      bqclient,
      reference,
      max_results,
      page_token,
      state_filter,
      min_creation_time,
      max_creation_time,
      all_users,
      parent_job_id,
  )['results']


def ListJobsWithTokenAndUnreachable(
    bqclient: bigquery_client.BigqueryClient,
    reference: Optional[bq_id_utils.ApiClientHelper.ProjectReference] = None,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    state_filter: Optional[Union[List[str], str]] = None,
    min_creation_time: Optional[str] = None,
    max_creation_time: Optional[str] = None,
    all_users: Optional[bool] = None,
    parent_job_id: Optional[str] = None,
):
  # pylint: disable=g-doc-args
  """Return a list of jobs.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    reference: The ProjectReference to list jobs for.
    max_results: The maximum number of jobs to return.
    page_token: Current page token (optional).
    state_filter: A single state filter or a list of filters to apply. If not
      specified, no filtering is applied.
    min_creation_time: Timestamp in milliseconds. Only return jobs created after
      or at this timestamp.
    max_creation_time: Timestamp in milliseconds. Only return jobs created
      before or at this timestamp.
    all_users: Whether to list jobs for all users of the project. Requesting
      user must be an owner of the project to list all jobs.
    parent_job_id: Retrieve only child jobs belonging to this parent; None to
      retrieve top-level jobs.

  Returns:
    A dict that contains enytries:
      'results': a list of jobs
      'token': nextPageToken for the last page, if present.
  """
  reference = bq_client_utils.NormalizeProjectReference(
      id_fallbacks=bqclient, reference=reference
  )
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ProjectReference,
      method='ListJobs',
  )
  if max_results is not None:
    if max_results > bq_processor_utils.MAX_RESULTS:
      max_results = bq_processor_utils.MAX_RESULTS
  request = bq_processor_utils.PrepareListRequest(
      reference, max_results, page_token
  )
  if state_filter is not None:
    # The apiclient wants enum values as lowercase strings.
    if isinstance(state_filter, str):
      state_filter = state_filter.lower()
    else:
      state_filter = [s.lower() for s in state_filter]
  bq_processor_utils.ApplyParameters(
      request,
      projection='full',
      state_filter=state_filter,
      all_users=all_users,
      parent_job_id=parent_job_id,
  )
  if min_creation_time is not None:
    request['minCreationTime'] = min_creation_time
  if max_creation_time is not None:
    request['maxCreationTime'] = max_creation_time
  result = bqclient.apiclient.jobs().list(**request).execute()
  results = result.get('jobs', [])
  if max_results is not None:
    while 'nextPageToken' in result and len(results) < max_results:
      request['maxResults'] = max_results - len(results)
      request['pageToken'] = result['nextPageToken']
      result = bqclient.apiclient.jobs().list(**request).execute()
      results.extend(result.get('jobs', []))
  response = dict(results=results)
  if 'nextPageToken' in result:
    response['token'] = result['nextPageToken']
  # The 'unreachable' field is a list of skipped locations that were
  # unreachable. The field definition is
  # google3/google/cloud/bigquery/v2/job.proto;rcl=622304818;l=593
  if 'unreachable' in result:
    response['unreachable'] = result['unreachable']
  return response


def CopyTable(
    bqclient: bigquery_client.BigqueryClient,
    source_references: List[bq_id_utils.ApiClientHelper.TableReference],
    dest_reference: bq_id_utils.ApiClientHelper.TableReference,
    create_disposition: Optional[str] = None,
    write_disposition: Optional[str] = None,  # Actually an enum.
    ignore_already_exists: Optional[bool] = False,
    encryption_configuration=None,
    operation_type: Optional[str] = 'COPY',  # Actually an enum.
    destination_expiration_time: Optional[str] = None,
    **kwds,
):
  """Copies a table.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    source_references: TableReferences of source tables.
    dest_reference: TableReference of destination table.
    create_disposition: Optional. Specifies the create_disposition for the
      dest_reference.
    write_disposition: Optional. Specifies the write_disposition for the
      dest_reference.
    ignore_already_exists: Whether to ignore "already exists" errors.
    encryption_configuration: Optional. Allows user to encrypt the table from
      the copy table command with Cloud KMS key. Passed as a dictionary in the
      following format: {'kmsKeyName': 'destination_kms_key'}
    **kwds: Passed on to ExecuteJob.

  Returns:
    The job description, or None for ignored errors.

  Raises:
    BigqueryDuplicateError: when write_disposition 'WRITE_EMPTY' is
      specified and the dest_reference table already exists.
  """
  for src_ref in source_references:
    bq_id_utils.typecheck(
        src_ref,
        bq_id_utils.ApiClientHelper.TableReference,
        method='CopyTable',
    )
  bq_id_utils.typecheck(
      dest_reference,
      bq_id_utils.ApiClientHelper.TableReference,
      method='CopyTable',
  )
  copy_config = {
      'destinationTable': dict(dest_reference),
      'sourceTables': [dict(src_ref) for src_ref in source_references],
  }
  if encryption_configuration:
    copy_config['destinationEncryptionConfiguration'] = encryption_configuration

  if operation_type:
    copy_config['operationType'] = operation_type

  if destination_expiration_time:
    copy_config['destinationExpirationTime'] = destination_expiration_time

  bq_processor_utils.ApplyParameters(
      copy_config,
      create_disposition=create_disposition,
      write_disposition=write_disposition,
  )

  try:
    return ExecuteJob(bqclient, {'copy': copy_config}, **kwds)
  except bq_error.BigqueryDuplicateError as e:
    if ignore_already_exists:
      return None
    raise e


def JobExists(
    bqclient: bigquery_client.BigqueryClient,
    reference: bq_id_utils.ApiClientHelper.JobReference,
) -> bool:
  """Returns true if the job exists."""
  bq_id_utils.typecheck(
      reference, bq_id_utils.ApiClientHelper.JobReference, method='JobExists'
  )
  try:
    return bqclient.apiclient.jobs().get(**dict(reference)).execute()
  except bq_error.BigqueryNotFoundError:
    return False


def DeleteJob(
    bqclient: bigquery_client.BigqueryClient,
    reference: bq_id_utils.ApiClientHelper.JobReference,
    ignore_not_found: Optional[bool] = False,
):
  """Deletes JobReference reference.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    reference: the JobReference to delete.
    ignore_not_found: Whether to ignore "not found" errors.

  Raises:
    BigqueryTypeError: if reference is not a JobReference.
    bq_error.BigqueryNotFoundError: if reference does not exist and
      ignore_not_found is False.
  """
  bq_id_utils.typecheck(
      reference, bq_id_utils.ApiClientHelper.JobReference, method='DeleteJob'
  )
  try:
    bqclient.apiclient.jobs().delete(**dict(reference)).execute()
  except bq_error.BigqueryNotFoundError:
    if not ignore_not_found:
      raise



#################################
## Job control
#################################


def StartJob(
    bqclient: bigquery_client.BigqueryClient,
    configuration,
    project_id: Optional[str] = None,
    upload_file: Optional[str] = None,
    job_id: Optional[str] = None,
    location: Optional[str] = None,
):
  """Start a job with the given configuration.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    configuration: The configuration for a job.
    project_id: The project_id to run the job under. If None,
      bqclient.project_id is used.
    upload_file: A file to include as a media upload to this request. Only valid
      on job requests that expect a media upload file.
    job_id: A unique job_id to use for this job. If a JobIdGenerator, a job id
      will be generated from the job configuration. If None, a unique job_id
      will be created for this request.
    location: Optional. The geographic location where the job should run.

  Returns:
    The job resource returned from the insert job request. If there is an
    error, the jobReference field will still be filled out with the job
    reference used in the request.

  Raises:
    bq_error.BigqueryClientConfigurationError: if project_id and
      bqclient.project_id are None.
  """
  project_id = project_id or bqclient.project_id
  if not project_id:
    raise bq_error.BigqueryClientConfigurationError(
        'Cannot start a job without a project id.'
    )
  configuration = configuration.copy()
  if bqclient.job_property:
    configuration['properties'] = dict(
        prop.partition('=')[0::2] for prop in bqclient.job_property
    )
  job_request = {'configuration': configuration}

  # Use the default job id generator if no job id was supplied.
  job_id = job_id or bqclient.job_id_generator

  if isinstance(job_id, bq_client_utils.JobIdGenerator):
    job_id = job_id.Generate(configuration)

  if job_id is not None:
    job_reference = {'jobId': job_id, 'projectId': project_id}
    job_request['jobReference'] = job_reference
    if location:
      job_reference['location'] = location
  media_upload = ''
  if upload_file:
    resumable = bqclient.enable_resumable_uploads
    # There is a bug in apiclient http lib that make uploading resumable files
    # with 0 length broken.
    if os.stat(upload_file).st_size == 0:
      resumable = False
    media_upload = http_request.MediaFileUpload(
        filename=upload_file,
        mimetype='application/octet-stream',
        resumable=resumable,
    )
  request = bqclient.apiclient.jobs().insert(
      body=job_request, media_body=media_upload, projectId=project_id
  )
  if upload_file and resumable:
    result = wait_printer.execute_in_chunks_with_progress(request)
  else:
    result = request.execute()
  return result


def _StartQueryRpc(
    bqclient: bigquery_client.BigqueryClient,
    query: str,
    dry_run: Optional[bool] = None,
    use_cache: Optional[bool] = None,
    preserve_nulls: Optional[bool] = None,
    request_id: Optional[str] = None,
    maximum_bytes_billed: Optional[int] = None,
    max_results: Optional[int] = None,
    timeout_ms: Optional[int] = None,
    job_timeout_ms: Optional[int] = None,
    max_slots: Optional[int] = None,
    min_completion_ratio: Optional[float] = None,
    project_id: Optional[str] = None,
    external_table_definitions_json=None,
    udf_resources=None,
    use_legacy_sql: Optional[bool] = None,
    location: Optional[str] = None,
    connection_properties=None,
    job_creation_mode: Optional[
        bigquery_client.BigqueryClient.JobCreationMode
    ] = None,
    labels: Optional[dict[str, str]] = None,
    reservation_id: Optional[str] = None,
    create_session: Optional[bool] = None,
    query_parameters=None,
    positional_parameter_mode=None,
    destination_encryption_configuration=None,
    **kwds,
):
  """Executes the given query using the rpc-style query api.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    query: Query to execute.
    dry_run: Optional. Indicates whether the query will only be validated and
      return processing statistics instead of actually running.
    use_cache: Optional. Whether to use the query cache. Caching is best-effort
      only and you should not make assumptions about whether or how long a query
      result will be cached.
    preserve_nulls: Optional. Indicates whether to preserve nulls in input data.
      Temporary flag; will be removed in a future version.
    request_id: Optional. The idempotency token for jobs.query
    maximum_bytes_billed: Optional. Upper limit on the number of billed bytes.
    max_results: Maximum number of results to return.
    timeout_ms: Timeout, in milliseconds, for the call to query().
    job_timeout_ms: Optional. How long to let the job run.
    max_slots: Optional. Cap on target rate of slot consumption by the query.
    min_completion_ratio: Optional. Specifies the minimum fraction of data that
      must be scanned before a query returns. This value should be between 0.0
      and 1.0 inclusive.
    project_id: Project id to use.
    external_table_definitions_json: Json representation of external table
      definitions.
    udf_resources: Array of inline and external UDF code resources.
    use_legacy_sql: The choice of using Legacy SQL for the query is optional. If
      not specified, the server will automatically determine the dialect based
      on query information, such as dialect prefixes. If no prefixes are found,
      it will default to Legacy SQL.
    location: Optional. The geographic location where the job should run.
    connection_properties: Optional. Connection properties to use when running
      the query, presented as a list of key/value pairs. A key of "time_zone"
      indicates that the query will be run with the default timezone
      corresponding to the value.
    job_creation_mode: Optional. An option for job creation. The valid values
      are JOB_CREATION_REQUIRED and JOB_CREATION_OPTIONAL.
    labels: Optional. Labels to be attached to the query.
    reservation_id: Optional. An option to set the reservation to use when
      execute the job. Reservation should be in the format of
      "project_id:reservation_id", "project_id:location.reservation_id", or
      "reservation_id".
    create_session: Optional. True to create a session for the query.
    query_parameters: parameter values for use_legacy_sql=False queries.
    positional_parameter_mode: If true, set the parameter mode to POSITIONAL
      instead of the default NAMED.
    destination_encryption_configuration: Optional. Allows user to encrypt the
      table created from a query job with a Cloud KMS key.
    **kwds: Extra keyword arguments passed directly to jobs.Query().

  Returns:
    The query response.

  Raises:
    bq_error.BigqueryClientConfigurationError: if project_id and
      bqclient.project_id are None.
    bq_error.BigqueryError: if query execution fails.
  """
  project_id = project_id or bqclient.project_id
  if not project_id:
    raise bq_error.BigqueryClientConfigurationError(
        'Cannot run a query without a project id.'
    )
  request = {'query': query}
  if external_table_definitions_json:
    request['tableDefinitions'] = external_table_definitions_json
  if udf_resources:
    request['userDefinedFunctionResources'] = udf_resources
  if bqclient.dataset_id:
    request['defaultDataset'] = bq_client_utils.GetQueryDefaultDataset(
        bqclient.dataset_id
    )

  # If the request id flag is set, generate a random one if it is not provided
  # explicitly.
  if request_id is None and flags.FLAGS.jobs_query_use_request_id:
    request_id = str(uuid.uuid4())

  reservation_path = _GetReservationPath(
      bqclient,
      reservation_id,
  )

  bq_processor_utils.ApplyParameters(
      request,
      preserve_nulls=preserve_nulls,
      request_id=request_id,
      maximum_bytes_billed=maximum_bytes_billed,
      use_query_cache=use_cache,
      timeout_ms=timeout_ms,
      job_timeout_ms=job_timeout_ms,
      max_slots=max_slots,
      max_results=max_results,
      use_legacy_sql=use_legacy_sql,
      min_completion_ratio=min_completion_ratio,
      job_creation_mode=job_creation_mode,
      reservation=reservation_path,
      location=location,
      create_session=create_session,
      query_parameters=query_parameters,
      destination_encryption_configuration=destination_encryption_configuration,
      parameter_mode=None
      if positional_parameter_mode is None
      else ('POSITIONAL' if positional_parameter_mode else 'NAMED'),
  )
  if labels:
    bq_processor_utils.ApplyParameters(request, labels=labels)
  bq_processor_utils.ApplyParameters(
      request, connection_properties=connection_properties
  )
  bq_processor_utils.ApplyParameters(request, dry_run=dry_run)
  logging.debug(
      'Calling bqclient.apiclient.jobs().query(%s, %s, %s)',
      request,
      project_id,
      kwds,
  )
  return (
      bqclient.apiclient.jobs()
      .query(body=request, projectId=project_id, **kwds)
      .execute()
  )


def GetQueryResults(
    bqclient: bigquery_client.BigqueryClient,
    job_id: Optional[str] = None,
    project_id: Optional[str] = None,
    max_results: Optional[int] = None,
    timeout_ms: Optional[int] = None,
    location: Optional[str] = None,
):
  """Waits for a query job to run and returns results if complete.

  By default, waits 10s for the provided job to complete and either returns
  the results or a response where jobComplete is set to false. The timeout can
  be increased but the call is not guaranteed to wait for the specified
  timeout.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    job_id: The job id of the query job that we are waiting to complete.
    project_id: The project id of the query job.
    max_results: The maximum number of results.
    timeout_ms: The number of milliseconds to wait for the query to complete.
    location: Optional. The geographic location of the job.

  Returns:
    The getQueryResults() result.

  Raises:
    bq_error.BigqueryClientConfigurationError: if project_id and
      bqclient.project_id are None.
  """
  project_id = project_id or bqclient.project_id
  if not project_id:
    raise bq_error.BigqueryClientConfigurationError(
        'Cannot get query results without a project id.'
    )
  kwds = {}
  bq_processor_utils.ApplyParameters(
      kwds,
      job_id=job_id,
      project_id=project_id,
      timeout_ms=timeout_ms,
      max_results=max_results,
      location=location,
  )
  return bqclient.apiclient.jobs().getQueryResults(**kwds).execute()


def RunJobSynchronously(
    bqclient: bigquery_client.BigqueryClient,
    configuration,
    project_id: Optional[str] = None,
    upload_file: Optional[str] = None,
    job_id: Optional[str] = None,
    location: Optional[str] = None,
):
  """Starts a job and waits for it to complete.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    configuration: The configuration for a job.
    project_id: The project_id to run the job under. If None,
      bqclient.project_id is used.
    upload_file: A file to include as a media upload to this request. Only valid
      on job requests that expect a media upload file.
    job_id: A unique job_id to use for this job. If a JobIdGenerator, a job id
      will be generated from the job configuration. If None, a unique job_id
      will be created for this request.
    location: Optional. The geographic location where the job should run.

  Returns:
    job, if it did not fail.

  Raises:
    BigQueryError: if the job fails.
  """
  result = StartJob(
      bqclient,
      configuration,
      project_id=project_id,
      upload_file=upload_file,
      job_id=job_id,
      location=location,
  )
  if result['status']['state'] != 'DONE':
    job_reference = bq_processor_utils.ConstructObjectReference(result)
    result = WaitJob(bqclient, job_reference)
  return bq_client_utils.RaiseIfJobError(result)


def ExecuteJob(
    bqclient: bigquery_client.BigqueryClient,
    configuration,
    sync: Optional[bool] = None,
    project_id: Optional[str] = None,
    upload_file: Optional[str] = None,
    job_id: Optional[str] = None,
    location: Optional[str] = None,
):
  """Execute a job, possibly waiting for results."""
  if sync is None:
    sync = bqclient.sync

  if sync:
    job = RunJobSynchronously(
        bqclient,
        configuration,
        project_id=project_id,
        upload_file=upload_file,
        job_id=job_id,
        location=location,
    )
  else:
    job = StartJob(
        bqclient,
        configuration,
        project_id=project_id,
        upload_file=upload_file,
        job_id=job_id,
        location=location,
    )
    bq_client_utils.RaiseIfJobError(job)
  return job


def CancelJob(
    bqclient: bigquery_client.BigqueryClient,
    project_id: Optional[str] = None,
    job_id: Optional[str] = None,
    location: Optional[str] = None,
):
  """Attempt to cancel the specified job if it is running.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    project_id: The project_id to the job is running under. If None,
      bqclient.project_id is used.
    job_id: The job id for this job.
    location: Optional. The geographic location of the job.

  Returns:
    The job resource returned for the job for which cancel is being requested.

  Raises:
    bq_error.BigqueryClientConfigurationError: if project_id or job_id
      are None.
  """
  project_id = project_id or bqclient.project_id
  if not project_id:
    raise bq_error.BigqueryClientConfigurationError(
        'Cannot cancel a job without a project id.'
    )
  if not job_id:
    raise bq_error.BigqueryClientConfigurationError(
        'Cannot cancel a job without a job id.'
    )

  job_reference = bq_id_utils.ApiClientHelper.JobReference.Create(
      projectId=project_id, jobId=job_id, location=location
  )
  result = (
      bqclient.apiclient.jobs().cancel(**dict(job_reference)).execute()['job']
  )
  if result['status']['state'] != 'DONE' and bqclient.sync:
    job_reference = bq_processor_utils.ConstructObjectReference(result)
    result = WaitJob(bqclient, job_reference=job_reference)
  return result


def WaitJob(
    bqclient: bigquery_client.BigqueryClient,
    job_reference: bq_id_utils.ApiClientHelper.JobReference,
    status: str = 'DONE',  # Should be an enum
    wait: int = sys.maxsize,
    wait_printer_factory: Optional[
        Callable[[], wait_printer.WaitPrinter]
    ] = None,
):
  """Poll for a job to run until it reaches the requested status.

  Arguments:
    bqclient: A BigqueryClient to get state and request clients from.
    job_reference: JobReference to poll.
    status: (optional, default 'DONE') Desired job status.
    wait: (optional, default maxint) Max wait time.
    wait_printer_factory: (optional, defaults to bqclient.wait_printer_factory)
      Returns a subclass of WaitPrinter that will be called after each job poll.

  Returns:
    The job object returned by the final status call.

  Raises:
    StopIteration: If polling does not reach the desired state before
      timing out.
    ValueError: If given an invalid wait value.
  """
  bq_id_utils.typecheck(
      job_reference,
      bq_id_utils.ApiClientHelper.JobReference,
      method='WaitJob',
  )
  start_time = time.time()
  job = None
  if wait_printer_factory:
    printer = wait_printer_factory()
  else:
    printer = bqclient.wait_printer_factory()

  # This is a first pass at wait logic: we ping at 1s intervals a few
  # times, then increase to max(3, max_wait), and then keep waiting
  # that long until we've run out of time.
  waits = itertools.chain(
     itertools.repeat(1, 8), range(2, 30, 3),
     itertools.repeat(30))
  current_wait = 0
  current_status = 'UNKNOWN'
  in_error_state = False
  while current_wait <= wait:
    try:
      done, job = PollJob(bqclient, job_reference, status=status, wait=wait)
      current_status = job['status']['state']
      in_error_state = False
      if done:
        printer.print(job_reference.jobId, current_wait, current_status)
        break
    except bq_error.BigqueryCommunicationError as e:
      # Communication errors while waiting on a job are okay.
      logging.warning('Transient error during job status check: %s', e)
    except bq_error.BigqueryBackendError as e:
      # Temporary server errors while waiting on a job are okay.
      logging.warning('Transient error during job status check: %s', e)
    except bq_error.BigqueryServiceError as e:
      # Among this catch-all class, some kinds are permanent
      # errors, so we don't want to retry indefinitely, but if
      # the error is transient we'd like "wait" to get past it.
      if in_error_state: raise
      in_error_state = True

    # For every second we're polling, update the message to the user.
    for _ in range(next(waits)):
      current_wait = time.time() - start_time
      printer.print(job_reference.jobId, current_wait, current_status)
      time.sleep(1)
  else:
    raise StopIteration(
        'Wait timed out. Operation not finished, in state %s'
        % (current_status,)
    )
  printer.done()
  return job


def PollJob(
    bqclient: bigquery_client.BigqueryClient,
    job_reference: bq_id_utils.ApiClientHelper.JobReference,
    status: str = 'DONE',  # Actrually an enum.
    wait: int = 0,
):
  """Poll a job once for a specific status.

  Arguments:
    bqclient: A BigqueryClient to get state and request clients from.
    job_reference: JobReference to poll.
    status: (optional, default 'DONE') Desired job status.
    wait: (optional, default 0) Max server-side wait time for one poll call.

  Returns:
    Tuple (in_state, job) where in_state is True if job is
    in the desired state.

  Raises:
    ValueError: If given an invalid wait value.
  """
  bq_id_utils.typecheck(
      job_reference,
      bq_id_utils.ApiClientHelper.JobReference,
      method='PollJob',
  )
  wait = bq_client_utils.NormalizeWait(wait)
  job = bqclient.apiclient.jobs().get(**dict(job_reference)).execute()
  current = job['status']['state']
  return (current == status, job)


#################################
## Wrappers for job types
#################################


def RunQuery(
    bqclient: bigquery_client.BigqueryClient,
    start_row: int,
    max_rows: int,
    **kwds,
):
  """Run a query job synchronously, and return the result.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    start_row: first row to read.
    max_rows: number of rows to read.
    **kwds: Passed on to Query.

  Returns:
    A tuple where the first item is the list of fields and the
    second item a list of rows.
  """
  new_kwds = dict(kwds)
  new_kwds['sync'] = True
  job = Query(bqclient, **new_kwds)

  return ReadSchemaAndJobRows(
      bqclient,
      job['jobReference'],
      start_row=start_row,
      max_rows=max_rows,
  )


def RunQueryRpc(
    bqclient: bigquery_client.BigqueryClient,
    query: str,
    dry_run: Optional[bool] = None,
    use_cache: Optional[bool] = None,
    preserve_nulls: Optional[bool] = None,
    request_id: Optional[str] = None,
    maximum_bytes_billed: Optional[int] = None,
    max_results: Optional[int] = None,
    wait: int = sys.maxsize,
    min_completion_ratio: Optional[float] = None,
    wait_printer_factory: Optional[
        Callable[[], wait_printer.WaitPrinter]
    ] = None,
    max_single_wait: Optional[int] = None,
    external_table_definitions_json=None,
    udf_resources=None,
    location: Optional[str] = None,
    connection_properties=None,
    job_creation_mode: Optional[
        bigquery_client.BigqueryClient.JobCreationMode
    ] = None,
    labels: Optional[dict[str, str]] = None,
    reservation_id: Optional[str] = None,
    job_timeout_ms: Optional[int] = None,
    max_slots: Optional[int] = None,
    **kwds,
):
  """Executes the given query using the rpc-style query api.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    query: Query to execute.
    dry_run: Optional. Indicates whether the query will only be validated and
      return processing statistics instead of actually running.
    use_cache: Optional. Whether to use the query cache. Caching is best-effort
      only and you should not make assumptions about whether or how long a query
      result will be cached.
    preserve_nulls: Optional. Indicates whether to preserve nulls in input data.
      Temporary flag; will be removed in a future version.
    request_id: Optional. Specifies the idempotency token for the request.
    maximum_bytes_billed: Optional. Upper limit on maximum bytes billed.
    max_results: Optional. Maximum number of results to return.
    wait: (optional, default maxint) Max wait time in seconds.
    min_completion_ratio: Optional. Specifies the minimum fraction of data that
      must be scanned before a query returns. This value should be between 0.0
      and 1.0 inclusive.
    wait_printer_factory: (optional, defaults to bqclient.wait_printer_factory)
      Returns a subclass of WaitPrinter that will be called after each job poll.
    max_single_wait: Optional. Maximum number of seconds to wait for each call
      to query() / getQueryResults().
    external_table_definitions_json: Json representation of external table
      definitions.
    udf_resources: Array of inline and remote UDF resources.
    location: Optional. The geographic location where the job should run.
    connection_properties: Optional. Connection properties to use when running
      the query, presented as a list of key/value pairs. A key of "time_zone"
      indicates that the query will be run with the default timezone
      corresponding to the value.
    job_creation_mode: Optional. An option for job creation. The valid values
      are JOB_CREATION_REQUIRED and JOB_CREATION_OPTIONAL.
    labels: Optional. Labels to be attached to the query.
    reservation_id: Optional. An option to set the reservation to use when
      execute the job. Reservation should be in the format of
      "project_id:reservation_id", "project_id:location.reservation_id", or
      "reservation_id".
    job_timeout_ms: Optional. How long to let the job run.
    max_slots: Optional. Cap on target rate of slot consumption by the query.
    **kwds: Passed directly to ExecuteSyncQuery.

  Raises:
    bq_error.BigqueryClientError: if no query is provided.
    StopIteration: if the query does not complete within wait seconds.
    bq_error.BigqueryError: if query fails.

  Returns:
    A tuple (schema fields, row results, execution metadata).
      For regular queries, the execution metadata dict contains
      the 'State' and 'status' elements that would be in a job result
      after FormatJobInfo(). If a job was not created, `queryId` is present;
      otherwise, `jobReference` is present.
      For dry run queries schema and rows are empty, the execution metadata
      dict contains statistics
  """

  if not bqclient.sync:
    raise bq_error.BigqueryClientError(
        'Running RPC-style query asynchronously is not supported'
    )
  if not query:
    raise bq_error.BigqueryClientError('No query string provided')

  if request_id is not None and not flags.FLAGS.jobs_query_use_request_id:
    raise bq_error.BigqueryClientError('request_id is not yet supported')

  if wait_printer_factory:
    printer = wait_printer_factory()
  else:
    printer = bqclient.wait_printer_factory()

  start_time = time.time()
  elapsed_time = 0
  job_reference = None
  query_id = None
  current_wait_ms = None
  while True:
    try:
      elapsed_time = 0 if job_reference is None else time.time() - start_time
      remaining_time = wait - elapsed_time
      if max_single_wait is not None:
        # Compute the current wait, being careful about overflow, since
        # remaining_time may be counting down from sys.maxint.
        current_wait_ms = int(min(remaining_time, max_single_wait) * 1000)
        if current_wait_ms < 0:
          current_wait_ms = sys.maxsize
      if remaining_time < 0:
        raise StopIteration('Wait timed out. Query not finished.')
      if job_reference is None:
        # We haven't yet run a successful Query(), so we don't
        # have a job id to check on.
        rows_to_read = max_results
        if bqclient.max_rows_per_request is not None:
          if rows_to_read is None:
            rows_to_read = bqclient.max_rows_per_request
          else:
            rows_to_read = min(bqclient.max_rows_per_request, int(rows_to_read))
        result = _StartQueryRpc(
            bqclient=bqclient,
            query=query,
            preserve_nulls=preserve_nulls,
            request_id=request_id,
            maximum_bytes_billed=maximum_bytes_billed,
            use_cache=use_cache,
            dry_run=dry_run,
            min_completion_ratio=min_completion_ratio,
            job_timeout_ms=job_timeout_ms,
            max_slots=max_slots,
            max_results=rows_to_read,
            external_table_definitions_json=external_table_definitions_json,
            udf_resources=udf_resources,
            location=location,
            connection_properties=connection_properties,
            job_creation_mode=job_creation_mode,
            labels=labels,
            reservation_id=reservation_id,
            **kwds,
        )
        if dry_run:
          execution = dict(
              statistics=dict(
                  query=dict(
                      totalBytesProcessed=result['totalBytesProcessed'],
                  )
              )
          )
          if 'cacheHit' in result:
            execution['statistics']['query']['cacheHit'] = result['cacheHit']
          if 'schema' in result:
            execution['statistics']['query']['schema'] = result['schema']
          return ([], [], execution)
        if 'jobReference' in result:
          job_reference = bq_id_utils.ApiClientHelper.JobReference.Create(
              **result['jobReference']
          )
        elif 'queryId' in result:
          # If a job was not created, we get a query_id and
          # the request is completed.
          query_id = result['queryId']
      else:
        # The query/getQueryResults methods do not return the job state,
        # so we just print 'RUNNING' while we are actively waiting.
        printer.print(job_reference.jobId, elapsed_time, 'RUNNING')
        result = GetQueryResults(
            bqclient,
            job_reference.jobId,
            max_results=max_results,
            timeout_ms=current_wait_ms,
            location=location,
        )
      if result['jobComplete']:
        (schema, rows) = ReadSchemaAndJobRows(
            bqclient,
            dict(job_reference) if job_reference else {},
            start_row=0,
            max_rows=max_results,
            result_first_page=result,
        )
        # If we get here, we must have succeeded.  We could still have
        # non-fatal errors though.
        status = {}
        if 'errors' in result:
          status['errors'] = result['errors']
        execution = {
            'State': 'SUCCESS',
            'status': status,
            'jobReference': job_reference,
            'queryId': query_id,
        }
        return (schema, rows, execution)
    except bq_error.BigqueryCommunicationError as e:
      # Communication errors while waiting on a job are okay.
      logging.warning('Transient error during query: %s', e)
    except bq_error.BigqueryBackendError as e:
      # Temporary server errors while waiting on a job are okay.
      logging.warning('Transient error during query: %s', e)


def Query(
    bqclient: bigquery_client.BigqueryClient,
    query: str,
    destination_table: Optional[str] = None,
    create_disposition: Optional[str] = None,
    write_disposition: Optional[str] = None,
    priority: Optional[str] = None,
    preserve_nulls: Optional[bool] = None,
    allow_large_results: Optional[bool] = None,
    dry_run: Optional[bool] = None,
    use_cache: Optional[bool] = None,
    min_completion_ratio: Optional[float] = None,
    flatten_results: Optional[bool] = None,
    external_table_definitions_json=None,
    udf_resources=None,
    maximum_billing_tier: Optional[int] = None,
    maximum_bytes_billed: Optional[int] = None,
    use_legacy_sql: Optional[bool] = None,
    schema_update_options: Optional[List[str]] = None,
    labels: Optional[Dict[str, str]] = None,
    query_parameters=None,
    time_partitioning=None,
    destination_encryption_configuration=None,
    clustering=None,
    range_partitioning=None,
    script_options=None,
    job_timeout_ms: Optional[int] = None,
    max_slots: Optional[int] = None,
    create_session: Optional[bool] = None,
    connection_properties=None,
    continuous=None,
    job_creation_mode: Optional[
        bigquery_client.BigqueryClient.JobCreationMode
    ] = None,
    reservation_id: Optional[str] = None,
    **kwds,
):
  # pylint: disable=g-doc-args
  """Execute the given query, returning the created job.

  The job will execute synchronously if sync=True is provided as an
  argument or if bqclient.sync is true.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    query: Query to execute.
    destination_table: (default None) If provided, send the results to the given
      table.
    create_disposition: Optional. Specifies the create_disposition for the
      destination_table.
    write_disposition: Optional. Specifies the write_disposition for the
      destination_table.
    priority: Optional. Priority to run the query with. Either 'INTERACTIVE'
      (default) or 'BATCH'.
    preserve_nulls: Optional. Indicates whether to preserve nulls in input data.
      Temporary flag; will be removed in a future version.
    allow_large_results: Enables larger destination table sizes.
    dry_run: Optional. Indicates whether the query will only be validated and
      return processing statistics instead of actually running.
    use_cache: Optional. Whether to use the query cache. If create_disposition
      is CREATE_NEVER, will only run the query if the result is already cached.
      Caching is best-effort only and you should not make assumptions about
      whether or how long a query result will be cached.
    min_completion_ratio: Optional. Specifies the minimum fraction of data that
      must be scanned before a query returns. This value should be between 0.0
      and 1.0 inclusive.
    flatten_results: Whether to flatten nested and repeated fields in the result
      schema. If not set, the default behavior is to flatten.
    external_table_definitions_json: Json representation of external table
      definitions.
    udf_resources: Array of inline and remote UDF resources.
    maximum_billing_tier: Upper limit for billing tier.
    maximum_bytes_billed: Upper limit for bytes billed.
    use_legacy_sql: The choice of using Legacy SQL for the query is optional. If
      not specified, the server will automatically determine the dialect based
      on query information, such as dialect prefixes. If no prefixes are found,
      it will default to Legacy SQL.
    schema_update_options: schema update options when appending to the
      destination table or truncating a table partition.
    labels: an optional dict of labels to set on the query job.
    query_parameters: parameter values for use_legacy_sql=False queries.
    time_partitioning: Optional. Provides time based partitioning specification
      for the destination table.
    clustering: Optional. Provides clustering specification for the destination
      table.
    destination_encryption_configuration: Optional. Allows user to encrypt the
      table created from a query job with a Cloud KMS key.
    range_partitioning: Optional. Provides range partitioning specification for
      the destination table.
    script_options: Optional. Options controlling script execution.
    job_timeout_ms: Optional. How long to let the job run.
    continuous: Optional. Whether the query should be executed as continuous
      query.
    job_creation_mode: Optional. An option for job creation. The valid values
      are JOB_CREATION_REQUIRED and JOB_CREATION_OPTIONAL.
    reservation_id: Optional. An option to set the reservation to use when
      execute the job. Reservation should be in the format of
      "project_id:reservation_id", "project_id:location.reservation_id", or
      "reservation_id". If reservation_id is "none", the job will be executed
      without assigned reservation using the on-demand slots.
    **kwds: Passed on to ExecuteJob.

  Raises:
    bq_error.BigqueryClientError: if no query is provided.

  Returns:
    The resulting job info.
  """
  if not query:
    raise bq_error.BigqueryClientError('No query string provided')
  query_config = {'query': query}
  if bqclient.dataset_id:
    query_config['defaultDataset'] = bq_client_utils.GetQueryDefaultDataset(
        bqclient.dataset_id
    )
  if external_table_definitions_json:
    query_config['tableDefinitions'] = external_table_definitions_json
  if udf_resources:
    query_config['userDefinedFunctionResources'] = udf_resources
  if destination_table:
    try:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=bqclient, identifier=destination_table
      )
    except bq_error.BigqueryError as e:
      raise bq_error.BigqueryError(
          'Invalid value %s for destination_table: %s' % (destination_table, e)
      )
    query_config['destinationTable'] = dict(reference)
  if destination_encryption_configuration:
    query_config['destinationEncryptionConfiguration'] = (
        destination_encryption_configuration
    )
  if script_options:
    query_config['scriptOptions'] = script_options
  if job_creation_mode:
    query_config['jobCreationMode'] = job_creation_mode.name
  bq_processor_utils.ApplyParameters(
      query_config,
      allow_large_results=allow_large_results,
      create_disposition=create_disposition,
      preserve_nulls=preserve_nulls,
      priority=priority,
      write_disposition=write_disposition,
      use_query_cache=use_cache,
      flatten_results=flatten_results,
      maximum_billing_tier=maximum_billing_tier,
      maximum_bytes_billed=maximum_bytes_billed,
      use_legacy_sql=use_legacy_sql,
      schema_update_options=schema_update_options,
      query_parameters=query_parameters,
      time_partitioning=time_partitioning,
      clustering=clustering,
      create_session=create_session,
      min_completion_ratio=min_completion_ratio,
      continuous=continuous,
      job_creation_mode=job_creation_mode,
      range_partitioning=range_partitioning,
  )
  bq_processor_utils.ApplyParameters(
      query_config, connection_properties=connection_properties
  )
  request = {'query': query_config}
  reservation_path = _GetReservationPath(
      bqclient,
      reservation_id,
      check_reservation_project=False,
  )
  bq_processor_utils.ApplyParameters(
      request,
      dry_run=dry_run,
      labels=labels,
      job_timeout_ms=job_timeout_ms,
      reservation=reservation_path,
  )
  bq_processor_utils.ApplyParameters(
      request,
      max_slots=max_slots,
  )
  return ExecuteJob(bqclient, request, **kwds)


def _GetReservationPath(
    bqclient: bigquery_client.BigqueryClient,
    reservation_id: Optional[str],
    check_reservation_project: bool = True,
) -> Optional[str]:
  """Converts the reservation_id from the format `<project_id>:<location>.<reservation_id>` to the fully qualified reservation path `projects/<project_id>/locations/<location>/reservations/<reservation_id>`.

  The special value "none" is returned as is.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    reservation_id: The reservation id to convert.
    check_reservation_project: Whether to validate the reservation project.

  Returns:
    The fully qualified reservation path or "none" if reservation_id is "none".
  """
  if reservation_id is None or reservation_id == 'none':
    return reservation_id
  reference = bq_client_utils.GetReservationReference(
      id_fallbacks=bqclient,
      identifier=reservation_id,
      default_location=bq_flags.LOCATION.value,
      check_reservation_project=check_reservation_project,
  )
  return reference.path()


def Load(
    bqclient: bigquery_client.BigqueryClient,
    destination_table_reference: bq_id_utils.ApiClientHelper.TableReference,
    source: str,
    schema=None,
    create_disposition: Optional[str] = None,
    write_disposition: Optional[str] = None,
    field_delimiter: Optional[str] = None,
    skip_leading_rows: Optional[bool] = None,
    encoding: Optional[str] = None,
    quote: Optional[str] = None,
    max_bad_records: Optional[int] = None,
    allow_quoted_newlines: Optional[bool] = None,
    source_format: Optional[str] = None,
    allow_jagged_rows: Optional[bool] = None,
    preserve_ascii_control_characters: Optional[bool] = None,
    ignore_unknown_values: Optional[bool] = None,
    projection_fields: Optional[List[str]] = None,
    autodetect: Optional[bool] = None,
    schema_update_options: Optional[List[str]] = None,
    null_marker: Optional[str] = None,
    null_markers: Optional[List[str]] = None,
    time_partitioning=None,
    clustering=None,
    destination_encryption_configuration=None,
    use_avro_logical_types: Optional[bool] = None,
    reference_file_schema_uri=None,
    range_partitioning=None,
    hive_partitioning_options=None,
    decimal_target_types=None,
    json_extension: Optional[str] = None,  # Actually an enum
    column_name_character_map=None,
    time_zone=None,
    date_format=None,
    datetime_format=None,
    time_format=None,
    timestamp_format=None,
    file_set_spec_type=None,
    thrift_options=None,
    parquet_options=None,
    connection_properties=None,
    reservation_id: Optional[str] = None,
    copy_files_only: Optional[bool] = None,
    source_column_match: Optional[str] = None,
    timestamp_target_precision: Optional[list[int]] = None,
    **kwds,
):
  """Load the given data into BigQuery.

  The job will execute synchronously if sync=True is provided as an
  argument or if bqclient.sync is true.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    destination_table_reference: TableReference to load data into.
    source: String specifying source data to load.
    schema: (default None) Schema of the created table. (Can be left blank for
      append operations.)
    create_disposition: Optional. Specifies the create_disposition for the
      destination_table_reference.
    write_disposition: Optional. Specifies the write_disposition for the
      destination_table_reference.
    field_delimiter: Optional. Specifies the single byte field delimiter.
    skip_leading_rows: Optional. Number of rows of initial data to skip.
    encoding: Optional. Specifies character encoding of the input data. May be
      "UTF-8" or "ISO-8859-1". Defaults to UTF-8 if not specified.
    quote: Optional. Quote character to use. Default is '"'. Note that quoting
      is done on the raw binary data before encoding is applied.
    max_bad_records: Optional. Maximum number of bad records that should be
      ignored before the entire job is aborted. Only supported for CSV and
      NEWLINE_DELIMITED_JSON file formats.
    allow_quoted_newlines: Optional. Whether to allow quoted newlines in CSV
      import data.
    source_format: Optional. Format of source data. May be "CSV",
      "DATASTORE_BACKUP", or "NEWLINE_DELIMITED_JSON".
    allow_jagged_rows: Optional. Whether to allow missing trailing optional
      columns in CSV import data.
    preserve_ascii_control_characters: Optional. Whether to preserve embedded
      Ascii Control characters in CSV import data.
    ignore_unknown_values: Optional. Whether to allow extra, unrecognized values
      in CSV or JSON data.
    projection_fields: Optional. If sourceFormat is set to "DATASTORE_BACKUP",
      indicates which entity properties to load into BigQuery from a Cloud
      Datastore backup.
    autodetect: Optional. If true, then we automatically infer the schema and
      options of the source files if they are CSV or JSON formats.
    schema_update_options: schema update options when appending to the
      destination table or truncating a table partition.
    null_marker: Optional. String that will be interpreted as a NULL value.
    null_markers: Optional. List of strings that will be interpreted as a NULL
      value.
    time_partitioning: Optional. Provides time based partitioning specification
      for the destination table.
    clustering: Optional. Provides clustering specification for the destination
      table.
    destination_encryption_configuration: Optional. Allows user to encrypt the
      table created from a load job with Cloud KMS key.
    use_avro_logical_types: Optional. Allows user to override default behaviour
      for Avro logical types. If this is set, Avro fields with logical types
      will be interpreted into their corresponding types (ie. TIMESTAMP),
      instead of only using their raw types (ie. INTEGER).
    reference_file_schema_uri: Optional. Allows user to provide a reference file
      with the reader schema, enabled for the format: AVRO, PARQUET, ORC.
    range_partitioning: Optional. Provides range partitioning specification for
      the destination table.
    hive_partitioning_options: (experimental) Options for configuring hive is
      picked if it is in the specified list and if it supports the precision and
      the scale. STRING supports all precision and scale values. If none of the
      listed types supports the precision and the scale, the type supporting the
      widest range in the specified list is picked, and if a value exceeds the
      supported range when reading the data, an error will be returned. This
      field cannot contain duplicate types. The order of the
    decimal_target_types: (experimental) Defines the list of possible SQL data
      types to which the source decimal values are converted. This list and the
      precision and the scale parameters of the decimal field determine the
      target type. In the order of NUMERIC, BIGNUMERIC, and STRING, a type is
      picked if it is in the specified list and if it supports the precision and
      the scale. STRING supports all precision and scale values. If none of the
      listed types supports the precision and the scale, the type supporting the
      widest range in the specified list is picked, and if a value exceeds the
      supported range when reading the data, an error will be returned. This
      field cannot contain duplicate types. The order of the types in this field
      is ignored. For example, ["BIGNUMERIC", "NUMERIC"] is the same as
      ["NUMERIC", "BIGNUMERIC"] and NUMERIC always takes precedence over
      BIGNUMERIC. Defaults to ["NUMERIC", "STRING"] for ORC and ["NUMERIC"] for
      the other file formats.
    json_extension: (experimental) Specify alternative parsing for JSON source
      format. To load newline-delimited JSON, specify 'GEOJSON'. Only applicable
      if `source_format` is 'NEWLINE_DELIMITED_JSON'.
    column_name_character_map: Indicates the character map used for column
      names. Specify 'STRICT' to use the latest character map and reject invalid
      column names. Specify 'V1' to support alphanumeric + underscore and name
      must start with a letter or underscore. Invalid column names will be
      normalized. Specify 'V2' to support flexible column name. Invalid column
      names will be normalized.
    file_set_spec_type: Set how to discover files for loading. Specify
      'FILE_SYSTEM_MATCH' (default behavior) to expand source URIs by listing
      files from the underlying object store. Specify
      'NEW_LINE_DELIMITED_MANIFEST' to parse the URIs as new line delimited
      manifest files, where each line contains a URI (No wild-card URIs are
      supported).
    thrift_options: (experimental) Options for configuring Apache Thrift load,
      which is required if `source_format` is 'THRIFT'.
    parquet_options: Options for configuring parquet files load, only applicable
      if `source_format` is 'PARQUET'.
    connection_properties: Optional. ConnectionProperties for load job.
    reservation_id: Optional. An option to set the reservation to use when
      execute the job. Reservation should be in the format of
      "project_id:reservation_id", "project_id:location.reservation_id", or
      "reservation_id".
    copy_files_only: Optional. True to configures the load job to only copy
      files to the destination BigLake managed table, without reading file
      content and writing them to new files.
    source_column_match: Optional. Controls the strategy used to match loaded
      columns to the schema.
    timestamp_target_precision: Precision (maximum number of total
      digits in base 10) for second of TIMESTAMP type.
      Available for the formats: CSV.
    **kwds: Passed on to ExecuteJob.

  Returns:
    The resulting job info.
  """
  bq_id_utils.typecheck(
      destination_table_reference, bq_id_utils.ApiClientHelper.TableReference
  )
  load_config = {'destinationTable': dict(destination_table_reference)}
  sources = bq_processor_utils.ProcessSources(source)
  if sources[0].startswith(bq_processor_utils.GCS_SCHEME_PREFIX):
    load_config['sourceUris'] = sources
    upload_file = None
  else:
    upload_file = sources[0]
  if schema is not None:
    load_config['schema'] = {'fields': bq_client_utils.ReadSchema(schema)}
  if use_avro_logical_types is not None:
    load_config['useAvroLogicalTypes'] = use_avro_logical_types
  if reference_file_schema_uri is not None:
    load_config['reference_file_schema_uri'] = reference_file_schema_uri
  if file_set_spec_type is not None:
    load_config['fileSetSpecType'] = file_set_spec_type
  if json_extension is not None:
    load_config['jsonExtension'] = json_extension
  if column_name_character_map is not None:
    load_config['columnNameCharacterMap'] = column_name_character_map
  if parquet_options is not None:
    load_config['parquetOptions'] = parquet_options
  load_config['decimalTargetTypes'] = decimal_target_types
  if destination_encryption_configuration:
    load_config['destinationEncryptionConfiguration'] = (
        destination_encryption_configuration
    )

  if time_zone is not None:
    load_config['timeZone'] = time_zone
  if date_format is not None:
    load_config['dateFormat'] = date_format
  if datetime_format is not None:
    load_config['datetimeFormat'] = datetime_format
  if time_format is not None:
    load_config['timeFormat'] = time_format
  if timestamp_format is not None:
    load_config['timestampFormat'] = timestamp_format

  if source_column_match is not None:
    load_config['sourceColumnMatch'] = source_column_match
  if timestamp_target_precision is not None:
    load_config['timestampTargetPrecision'] = timestamp_target_precision

  bq_processor_utils.ApplyParameters(
      load_config,
      create_disposition=create_disposition,
      write_disposition=write_disposition,
      field_delimiter=field_delimiter,
      skip_leading_rows=skip_leading_rows,
      encoding=encoding,
      quote=quote,
      max_bad_records=max_bad_records,
      source_format=source_format,
      allow_quoted_newlines=allow_quoted_newlines,
      allow_jagged_rows=allow_jagged_rows,
      preserve_ascii_control_characters=preserve_ascii_control_characters,
      ignore_unknown_values=ignore_unknown_values,
      projection_fields=projection_fields,
      schema_update_options=schema_update_options,
      null_marker=null_marker,
      null_markers=null_markers,
      time_partitioning=time_partitioning,
      clustering=clustering,
      autodetect=autodetect,
      range_partitioning=range_partitioning,
      hive_partitioning_options=hive_partitioning_options,
      thrift_options=thrift_options,
      connection_properties=connection_properties,
      copy_files_only=copy_files_only,
      parquet_options=parquet_options,
  )
  configuration = {'load': load_config}
  if reservation_id is not None:
    reference = bq_client_utils.GetReservationReference(
        id_fallbacks=bqclient,
        identifier=reservation_id,
        default_location=bq_flags.LOCATION.value,
        check_reservation_project=False,
    )
    configuration['reservation'] = reference.path()
  return ExecuteJob(
      bqclient, configuration=configuration, upload_file=upload_file, **kwds
  )




def Extract(
    bqclient: bigquery_client.BigqueryClient,
    reference: bq_id_utils.ApiClientHelper.TableReference,
    destination_uris: str,
    print_header: Optional[bool] = None,
    field_delimiter: Optional[str] = None,
    destination_format: Optional[str] = None,  # Actually an enum.
    trial_id=None,
    add_serving_default_signature=None,
    compression: Optional[str] = None,  # Actually an enum.
    use_avro_logical_types: Optional[bool] = None,
    reservation_id: Optional[str] = None,
    **kwds,
):
  """Extract the given table from BigQuery.

  The job will execute synchronously if sync=True is provided as an
  argument or if bqclient.sync is true.

  Args:
    bqclient: A BigqueryClient to get state and request clients from.
    reference: TableReference to read data from.
    destination_uris: String specifying one or more destination locations,
      separated by commas.
    print_header: Optional. Whether to print out a header row in the results.
    field_delimiter: Optional. Specifies the single byte field delimiter.
    destination_format: Optional. Format to extract table to. May be "CSV",
      "AVRO" or "NEWLINE_DELIMITED_JSON".
    trial_id: Optional. 1-based ID of the trial to be exported from a
      hyperparameter tuning model.
    add_serving_default_signature: Optional. Whether to add serving_default
      signature for BigQuery ML trained tf based models.
    compression: Optional. The compression type to use for exported files.
      Possible values include "GZIP" and "NONE". The default value is NONE.
    use_avro_logical_types: Optional. Whether to use avro logical types for
      applicable column types on extract jobs.
    reservation_id: Optional. An option to set the reservation to use when
      execute the job. Reservation should be in the format of
      "project_id:reservation_id", "project_id:location.reservation_id", or
      "reservation_id".
    **kwds: Passed on to ExecuteJob.

  Returns:
    The resulting job info.

  Raises:
    bq_error.BigqueryClientError: if required parameters are invalid.
  """
  bq_id_utils.typecheck(
      reference,
      (
          bq_id_utils.ApiClientHelper.TableReference,
          bq_id_utils.ApiClientHelper.ModelReference,
      ),
      method='Extract',
  )
  uris = destination_uris.split(',')
  for uri in uris:
    if not uri.startswith(bq_processor_utils.GCS_SCHEME_PREFIX):
      raise bq_error.BigqueryClientError(
          'Illegal URI: {}. Extract URI must start with "{}".'.format(
              uri, bq_processor_utils.GCS_SCHEME_PREFIX
          )
      )
  extract_config = {}
  if isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
    extract_config = {'sourceTable': dict(reference)}
  elif isinstance(reference, bq_id_utils.ApiClientHelper.ModelReference):
    extract_config = {'sourceModel': dict(reference)}
    if trial_id:
      extract_config.update({'modelExtractOptions': {'trialId': trial_id}})
    if add_serving_default_signature:
      extract_config.update({
          'modelExtractOptions': {
              'addServingDefaultSignature': add_serving_default_signature
          }
      })
  bq_processor_utils.ApplyParameters(
      extract_config,
      destination_uris=uris,
      destination_format=destination_format,
      print_header=print_header,
      field_delimiter=field_delimiter,
      compression=compression,
      use_avro_logical_types=use_avro_logical_types,
  )
  configuration = {'extract': extract_config}
  if reservation_id is not None:
    reference = bq_client_utils.GetReservationReference(
        id_fallbacks=bqclient,
        identifier=reservation_id,
        default_location=bq_flags.LOCATION.value,
        check_reservation_project=False,
    )
    configuration['reservation'] = reference.path()
  return ExecuteJob(bqclient, configuration=configuration, **kwds)
