#!/usr/bin/env python
"""The BigQuery CLI data transfer client library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
from typing import Any, Dict, NamedTuple, Optional

from googleapiclient import discovery

from clients import utils as bq_client_utils
from utils import bq_api_utils
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

Service = bq_api_utils.Service

# Data Transfer Service Authorization Info
AUTHORIZATION_CODE = 'authorization_code'
VERSION_INFO = 'version_info'


class TransferScheduleArgs:
  """Arguments to customize data transfer schedule."""

  def __init__(
      self,
      schedule: Optional[str] = None,
      start_time: Optional[str] = None,
      end_time: Optional[str] = None,
      disable_auto_scheduling: Optional[bool] = False,
      event_driven_schedule: Optional[str] = None,
  ):
    self.schedule = schedule
    self.start_time = start_time
    self.end_time = end_time
    self.disable_auto_scheduling = disable_auto_scheduling
    self.event_driven_schedule = event_driven_schedule

  def to_schedule_options_v2_payload(
      self, options_to_copy: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:
    """Returns a dictionary of schedule options v2.

    Args:
      options_to_copy: Existing options to copy from.

    Returns:
      A dictionary of schedule options v2 expected by the
      bigquery.transfers.create and bigquery.transfers.update API methods.

    Raises:
      bq_error.BigqueryError: If shedule options conflict.
    """
    self._validate_schedule_options()

    options = {}
    if self.event_driven_schedule:
      options['eventDrivenSchedule'] = self._process_event_driven_schedule(
          self.event_driven_schedule
      )
    elif self.disable_auto_scheduling:
      options['manualSchedule'] = {}
    else:
      options['timeBasedSchedule'] = {}
      if options_to_copy and 'timeBasedSchedule' in options_to_copy:
        options['timeBasedSchedule'] = dict(
            options_to_copy['timeBasedSchedule']
        )
      if self.schedule:
        options['timeBasedSchedule']['schedule'] = self.schedule
      if self.start_time:
        options['timeBasedSchedule']['startTime'] = self._time_or_infitity(
            self.start_time
        )
      if self.end_time:
        options['timeBasedSchedule']['endTime'] = self._time_or_infitity(
            self.end_time
        )
    return options

  def to_schedule_options_payload(
      self, options_to_copy: Optional[Dict[str, str]] = None
  ) -> Dict[str, Any]:
    """Returns a dictionary of schedule options.

    Args:
      options_to_copy: Existing options to be copied.

    Returns:
      A dictionary of schedule options expected by the
      bigquery.transfers.create and bigquery.transfers.update API methods.
    """

    # Copy the current options or start with an empty dictionary.
    options = dict(options_to_copy or {})

    if self.start_time is not None:
      options['startTime'] = self._time_or_infitity(self.start_time)
    if self.end_time is not None:
      options['endTime'] = self._time_or_infitity(self.end_time)

    options['disableAutoScheduling'] = self.disable_auto_scheduling

    return options

  def _time_or_infitity(self, time_str: str):
    """Returns None to indicate Inifinity, if time_str is an empty string."""
    return time_str or None

  def _validate_schedule_options(self):
    """Validates schedule options.

    Raises:
      bq_error.BigqueryError: If the given schedule options conflict.
    """
    is_time_based_schedule = any(
        [self.schedule, self.start_time, self.end_time]
    )
    is_event_driven_schedule = self.event_driven_schedule is not None
    if (
        sum([
            self.disable_auto_scheduling,
            is_time_based_schedule,
            is_event_driven_schedule,
        ])
    ) > 1:
      raise bq_error.BigqueryError(
          'The provided scheduling options conflict. Please specify one of'
          ' no_auto_scheduling, time-based schedule or event-driven schedule.'
      )

  def _process_event_driven_schedule(
      self,
      event_driven_schedule: str,
  ) -> Dict[str, str]:
    """Processes the event_driven_schedule given in JSON format.

    Args:
      event_driven_schedule: The user specified event driven schedule. This
        should be in JSON format given as a string. Ex:
        --event_driven_schedule='{"pubsub_subscription":"subscription"}'.

    Returns:
      parsed_event_driven_schedule: The parsed event driven schedule.

    Raises:
      bq_error.BigqueryError: If there is an error with the given params.
    """
    try:
      parsed_event_driven_schedule = json.loads(event_driven_schedule)
    except Exception as e:
      raise bq_error.BigqueryError(
          'Event driven schedule should be specified in JSON format.'
      ) from e
    if 'pubsub_subscription' not in parsed_event_driven_schedule:
      raise bq_error.BigqueryError(
          'Must specify pubsub_subscription in --event_driven_schedule.'
      )
    return parsed_event_driven_schedule


def get_transfer_config(transfer_client: discovery.Resource, transfer_id: str):
  return (
      transfer_client.projects()
      .locations()
      .transferConfigs()
      .get(name=transfer_id)
      .execute()
  )


def get_transfer_run(transfer_client: discovery.Resource, identifier: str):
  return (
      transfer_client.projects()
      .locations()
      .transferConfigs()
      .runs()
      .get(name=identifier)
      .execute()
  )


def list_transfer_configs(
    transfer_client: discovery.Resource,
    reference: Optional[bq_id_utils.ApiClientHelper.ProjectReference] = None,
    location: Optional[str] = None,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    data_source_ids: Optional[str] = None,
):
  """Return a list of transfer configurations.

  Args:
    transfer_client: the transfer client to use.
    reference: The ProjectReference to list transfer configurations for.
    location: The location id, e.g. 'us' or 'eu'.
    page_size: The maximum number of transfer configurations to return.
    page_token: Current page token (optional).
    data_source_ids: The dataSourceIds to display transfer configurations for.

  Returns:
    A list of transfer configurations.
  """
  results = None
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ProjectReference,
      method='list_transfer_configs',
  )
  if page_size is not None:
    if page_size > bq_processor_utils.MAX_RESULTS:
      page_size = bq_processor_utils.MAX_RESULTS
  request = bq_processor_utils.PrepareTransferListRequest(
      reference, location, page_size, page_token, data_source_ids
  )
  if request:
    bq_processor_utils.ApplyParameters(request)
    result = (
        transfer_client.projects()
        .locations()
        .transferConfigs()
        .list(**request)
        .execute()
    )
    results = result.get('transferConfigs', [])
    if page_size is not None:
      while 'nextPageToken' in result and len(results) < page_size:
        request = bq_processor_utils.PrepareTransferListRequest(
            reference,
            location,
            page_size - len(results),
            result['nextPageToken'],
            data_source_ids,
        )
        if request:
          bq_processor_utils.ApplyParameters(request)
          result = (
              transfer_client.projects()
              .locations()
              .transferConfigs()
              .list(**request)
              .execute()
          )
          results.extend(result.get('nextPageToken', []))
        else:
          return
    if len(results) < 1:
      logging.info('There are no transfer configurations to be shown.')
    if result.get('nextPageToken'):
      return (results, result.get('nextPageToken'))
  return (results,)


def list_transfer_runs(
    transfer_client: discovery.Resource,
    reference: Optional[bq_id_utils.ApiClientHelper.TransferConfigReference],
    run_attempt: Optional[str],
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
    states: Optional[str] = None,
):
  """Return a list of transfer runs.

  Args:
    transfer_client: the transfer client to use.
    reference: The ProjectReference to list transfer runs for.
    run_attempt: Which runs should be pulled. The default value is 'LATEST',
      which only returns the latest run per day. To return all runs, please
      specify 'RUN_ATTEMPT_UNSPECIFIED'.
    max_results: The maximum number of transfer runs to return (optional).
    page_token: Current page token (optional).
    states: States to filter transfer runs (optional).

  Returns:
    A list of transfer runs.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TransferConfigReference,
      method='list_transfer_runs',
  )
  reference = str(reference)
  request = bq_processor_utils.PrepareTransferRunListRequest(
      reference, run_attempt, max_results, page_token, states
  )
  response = (
      transfer_client.projects()
      .locations()
      .transferConfigs()
      .runs()
      .list(**request)
      .execute()
  )
  transfer_runs = response.get('transferRuns', [])
  if max_results is not None:
    while 'nextPageToken' in response and len(transfer_runs) < max_results:
      page_token = response.get('nextPageToken')
      max_results -= len(transfer_runs)
      request = bq_processor_utils.PrepareTransferRunListRequest(
          reference, run_attempt, max_results, page_token, states
      )
      response = (
          transfer_client.projects()
          .locations()
          .transferConfigs()
          .runs()
          .list(**request)
          .execute()
      )
      transfer_runs.extend(response.get('transferRuns', []))
    if response.get('nextPageToken'):
      return (transfer_runs, response.get('nextPageToken'))
  return (transfer_runs,)


def list_transfer_logs(
    transfer_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TransferRunReference,
    message_type: Optional[str] = None,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
):
  """Return a list of transfer run logs.

  Args:
    transfer_client: the transfer client to use.
    reference: The ProjectReference to list transfer run logs for.
    message_type: Message types to return.
    max_results: The maximum number of transfer run logs to return.
    page_token: Current page token (optional).

  Returns:
    A list of transfer run logs.
  """
  reference = str(reference)
  request = bq_processor_utils.PrepareListTransferLogRequest(
      reference,
      max_results=max_results,
      page_token=page_token,
      message_type=message_type,
  )
  response = (
      transfer_client.projects()
      .locations()
      .transferConfigs()
      .runs()
      .transferLogs()
      .list(**request)
      .execute()
  )
  transfer_logs = response.get('transferMessages', [])
  if max_results is not None:
    while 'nextPageToken' in response and len(transfer_logs) < max_results:
      page_token = response['nextPageToken']
      max_results -= len(transfer_logs)
      request = bq_processor_utils.PrepareListTransferLogRequest(
          reference,
          max_results=max_results,
          page_token=page_token,
          message_type=message_type,
      )
      response = (
          transfer_client.projects()
          .locations()
          .transferConfigs()
          .runs()
          .transferLogs()
          .list(**request)
          .execute()
      )
      transfer_logs.extend(response.get('transferMessages', []))
  if response.get('nextPageToken'):
    return (transfer_logs, response.get('nextPageToken'))
  return (transfer_logs,)


def start_manual_transfer_runs(
    transfer_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TransferConfigReference,
    start_time: Optional[str],
    end_time: Optional[str],
    run_time: Optional[str],
):
  """Starts manual transfer runs.

  Args:
    transfer_client: the transfer client to use.
    reference: Transfer configuration name for the run.
    start_time: Start time of the range of transfer runs.
    end_time: End time of the range of transfer runs.
    run_time: Specific time for a transfer run.

  Returns:
    The list of started transfer runs.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TransferConfigReference,
      method='start_manual_transfer_runs',
  )
  parent = str(reference)

  if run_time:
    body = {'requestedRunTime': run_time}
  else:
    body = {
        'requestedTimeRange': {'startTime': start_time, 'endTime': end_time}
    }

  configs_request = transfer_client.projects().locations().transferConfigs()
  response = configs_request.startManualRuns(parent=parent, body=body).execute()

  return response.get('runs')


def transfer_exists(
    transfer_client: discovery.Resource,
    reference: 'bq_id_utils.ApiClientHelper.TransferConfigReference',
) -> bool:
  """Returns true if the transfer exists."""
  # pylint: disable=missing-function-docstring
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TransferConfigReference,
      method='transfer_exists',
  )
  try:
    transfer_client.projects().locations().transferConfigs().get(
        name=reference.transferConfigName
    ).execute()
    return True
  except bq_error.BigqueryNotFoundError:
    return False


def _fetch_data_source(
    transfer_client: discovery.Resource,
    project_reference: str,
    data_source_id: str,
):
  data_source_retrieval = (
      project_reference + '/locations/-/dataSources/' + data_source_id
  )

  return (
      transfer_client.projects()
      .locations()
      .dataSources()
      .get(name=data_source_retrieval)
      .execute()
  )


def update_transfer_config(
    transfer_client: discovery.Resource,
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    reference: bq_id_utils.ApiClientHelper.TransferConfigReference,
    target_dataset: Optional[str] = None,
    display_name: Optional[str] = None,
    refresh_window_days: Optional[str] = None,
    params: Optional[str] = None,
    auth_info: Optional[Dict[str, str]] = None,
    service_account_name: Optional[str] = None,
    destination_kms_key: Optional[str] = None,
    notification_pubsub_topic: Optional[str] = None,
    schedule_args: Optional[TransferScheduleArgs] = None,
):
  """Updates a transfer config.

  Args:
    transfer_client: the transfer client to use.
    id_fallbacks: IDs to use when they have not been explicitly specified.
    reference: the TransferConfigReference to update.
    target_dataset: Optional updated target dataset.
    display_name: Optional change to the display name.
    refresh_window_days: Optional update to the refresh window days. Some data
      sources do not support this.
    params: Optional parameters to update.
    auth_info: A dict contains authorization info which can be either an
      authorization_code or a version_info that the user input if they want to
      update credentials.
    service_account_name: The service account that the user could act as and
      used as the credential to create transfer runs from the transfer config.
    destination_kms_key: Optional KMS key for encryption.
    notification_pubsub_topic: The Pub/Sub topic where notifications will be
      sent after transfer runs associated with this transfer config finish.
    schedule_args: Optional parameters to customize data transfer schedule.

  Raises:
    BigqueryTypeError: if reference is not a TransferConfigReference.
    bq_error.BigqueryError: required field not given.
  """

  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TransferConfigReference,
      method='update_transfer_config',
  )
  project_reference = 'projects/' + (
      bq_client_utils.GetProjectReference(id_fallbacks=id_fallbacks).projectId
  )
  current_config = get_transfer_config(
      transfer_client, reference.transferConfigName
  )
  update_mask = []
  update_items = {}
  update_items['dataSourceId'] = current_config['dataSourceId']
  if target_dataset:
    update_items['destinationDatasetId'] = target_dataset
    update_mask.append('transfer_config.destination_dataset_id')

  if display_name:
    update_mask.append('transfer_config.display_name')
    update_items['displayName'] = display_name

  if params:
    update_items = bq_processor_utils.ProcessParamsFlag(params, update_items)
    update_mask.append('transfer_config.params')

  # if refresh window provided, check that data source supports it
  if refresh_window_days:
    data_source_info = _fetch_data_source(
        transfer_client, project_reference, current_config['dataSourceId']
    )
    update_items = bq_processor_utils.ProcessRefreshWindowDaysFlag(
        refresh_window_days,
        data_source_info,
        update_items,
        current_config['dataSourceId'],
    )
    update_mask.append('transfer_config.data_refresh_window_days')

  if schedule_args:
    update_items['scheduleOptionsV2'] = (
        schedule_args.to_schedule_options_v2_payload(
            current_config.get('scheduleOptionsV2')
        )
    )
    update_mask.append('transfer_config.scheduleOptionsV2')

  if notification_pubsub_topic:
    update_items['notification_pubsub_topic'] = notification_pubsub_topic
    update_mask.append('transfer_config.notification_pubsub_topic')

  if auth_info is not None and AUTHORIZATION_CODE in auth_info:
    update_mask.append(AUTHORIZATION_CODE)

  if auth_info is not None and VERSION_INFO in auth_info:
    update_mask.append(VERSION_INFO)

  if service_account_name:
    update_mask.append('service_account_name')

  if destination_kms_key:
    update_items['encryption_configuration'] = {
        'kms_key_name': {'value': destination_kms_key}
    }
    update_mask.append('encryption_configuration.kms_key_name')

  try:
    transfer_client.projects().locations().transferConfigs().patch(
        body=update_items,
        name=reference.transferConfigName,
        updateMask=','.join(update_mask),
        authorizationCode=(
            None if auth_info is None else auth_info.get(AUTHORIZATION_CODE)
        ),
        versionInfo=None if auth_info is None else auth_info.get(VERSION_INFO),
        serviceAccountName=service_account_name,
        x__xgafv='2',
    ).execute()
  except bq_error.BigqueryInterfaceError as e:
    if target_dataset and 'Not found: Dataset' in str(e):
      dataset_reference = bq_client_utils.GetDatasetReference(
          id_fallbacks=id_fallbacks, identifier=target_dataset
      )
      raise bq_error.BigqueryNotFoundError(
          'Not found: %r' % (dataset_reference,), {'reason': 'notFound'}, []
      ) from e
    else:
      raise e


def create_transfer_config(
    transfer_client: discovery.Resource,
    reference: str,
    data_source: str,
    target_dataset: Optional[str] = None,
    display_name: Optional[str] = None,
    refresh_window_days: Optional[str] = None,
    params: Optional[str] = None,
    auth_info: Optional[Dict[str, str]] = None,
    service_account_name: Optional[str] = None,
    notification_pubsub_topic: Optional[str] = None,
    schedule_args: Optional[TransferScheduleArgs] = None,
    destination_kms_key: Optional[str] = None,
    managed_table_type: Optional[str] = None,
    location: Optional[str] = None,
):
  """Create a transfer config corresponding to TransferConfigReference.

  Args:
    transfer_client: the transfer client to use.
    reference: the TransferConfigReference to create.
    data_source: The data source for the transfer config.
    target_dataset: The dataset where the new transfer config will exist.
    display_name: A display name for the transfer config.
    refresh_window_days: Refresh window days for the transfer config.
    params: Parameters for the created transfer config. The parameters should be
      in JSON format given as a string. Ex: --params="{'param':'value'}". The
      params should be the required values needed for each data source and will
      vary.
    auth_info: A dict contains authorization info which can be either an
      authorization_code or a version_info that the user input if they need
      credentials.
    service_account_name: The service account that the user could act as and
      used as the credential to create transfer runs from the transfer config.
    notification_pubsub_topic: The Pub/Sub topic where notifications will be
      sent after transfer runs associated with this transfer config finish.
    schedule_args: Optional parameters to customize data transfer schedule.
    destination_kms_key: Optional KMS key for encryption.
    managed_table_type: Optional destination table type for the transfer config.
    location: The location where the new transfer config will run.

  Raises:
    BigqueryNotFoundError: if a requested item is not found.
    bq_error.BigqueryError: if a required field isn't provided.

  Returns:
    The generated transfer configuration name.
  """
  create_items = {}

  # The backend will check if the dataset exists.
  if target_dataset:
    create_items['destinationDatasetId'] = target_dataset

  if display_name:
    create_items['displayName'] = display_name
  else:
    raise bq_error.BigqueryError('A display name must be provided.')

  create_items['dataSourceId'] = data_source

  # if refresh window provided, check that data source supports it
  if refresh_window_days:
    data_source_info = _fetch_data_source(
        transfer_client, reference, data_source
    )
    create_items = bq_processor_utils.ProcessRefreshWindowDaysFlag(
        refresh_window_days, data_source_info, create_items, data_source
    )

  # checks that all required params are given
  # if a param that isn't required is provided, it is ignored.
  if params:
    create_items = bq_processor_utils.ProcessParamsFlag(params, create_items)
  else:
    raise bq_error.BigqueryError('Parameters must be provided.')

  if location:
    parent = reference + '/locations/' + location
  else:
    # The location is infererred by the data transfer service from the
    # dataset location.
    parent = reference + '/locations/-'

  if schedule_args:
    create_items['scheduleOptionsV2'] = (
        schedule_args.to_schedule_options_v2_payload()
    )

  if notification_pubsub_topic:
    create_items['notification_pubsub_topic'] = notification_pubsub_topic

  if destination_kms_key:
    create_items['encryption_configuration'] = {
        'kms_key_name': {'value': destination_kms_key}
    }

  if managed_table_type:
    create_items['managed_table_type'] = managed_table_type

  new_transfer_config = (
      transfer_client.projects()
      .locations()
      .transferConfigs()
      .create(
          parent=parent,
          body=create_items,
          authorizationCode=(
              None if auth_info is None else auth_info.get(AUTHORIZATION_CODE)
          ),
          versionInfo=None
          if auth_info is None
          else auth_info.get(VERSION_INFO),
          serviceAccountName=service_account_name,
      )
      .execute()
  )

  return new_transfer_config['name']


def delete_transfer_config(
    transfer_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.TransferConfigReference,
    ignore_not_found: bool = False,
):
  """Deletes TransferConfigReference reference.

  Args:
    transfer_client: the transfer client to use.
    reference: the TransferConfigReference to delete.
    ignore_not_found: Whether to ignore "not found" errors.

  Raises:
    BigqueryTypeError: if reference is not a TransferConfigReference.
    bq_error.BigqueryNotFoundError: if reference does not exist and
      ignore_not_found is False.
  """

  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.TransferConfigReference,
      method='delete_transfer_config',
  )
  try:
    transfer_client.projects().locations().transferConfigs().delete(
        name=reference.transferConfigName
    ).execute()
  except bq_error.BigqueryNotFoundError as e:
    if not ignore_not_found:
      raise bq_error.BigqueryNotFoundError(
          'Not found: %r' % (reference,), {'reason': 'notFound'}, []
      ) from e
