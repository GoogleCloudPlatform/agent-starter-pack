#!/usr/bin/env python
"""The show command for the BQ CLI."""

from typing import Optional

from absl import app
from absl import flags

import bq_flags
from clients import client_connection
from clients import client_data_transfer
from clients import client_dataset
from clients import client_deprecated
from clients import client_reservation
from clients import client_row_access_policy
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import utils as bq_frontend_utils
from frontend import utils_id as frontend_id_utils
from utils import bq_error
from utils import bq_id_utils


ApiClientHelper = bq_id_utils.ApiClientHelper
DatasetReference = bq_id_utils.ApiClientHelper.DatasetReference
TransferConfigReference = bq_id_utils.ApiClientHelper.TransferConfigReference
TransferRunReference = bq_id_utils.ApiClientHelper.TransferRunReference
EncryptionServiceAccount = bq_id_utils.ApiClientHelper.EncryptionServiceAccount


class Show(bigquery_command.BigqueryCmd):
  """The BQ CLI command to display a resource to the user."""

  usage = """show [<identifier>]"""
  command = 'show'

  def __init__(self, name: str, fv: flags.FlagValues) -> None:
    super(Show, self).__init__(name, fv)
    flags.DEFINE_boolean(
        'job',
        False,
        'If true, interpret this identifier as a job id.',
        short_name='j',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'dataset',
        False,
        'Show dataset with this name.',
        short_name='d',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'view',
        False,
        'Show view specific details instead of general table details.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'materialized_view',
        False,
        'Show materialized view specific details instead of general table '
        'details.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'table_replica',
        False,
        'Show table replica specific details instead of general table details.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'schema',
        False,
        'Show only the schema instead of general table details.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'encryption_service_account',
        False,
        'Show the service account for a user if it exists, or create one '
        'if it does not exist.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'transfer_config',
        False,
        'Show transfer configuration for configuration resource name.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'transfer_run',
        False,
        'Show information about the particular transfer run.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'model',
        False,
        'Show details of model with this model ID.',
        short_name='m',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'routine',
        False,
        'Show the details of a particular routine.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation',
        None,
        'Shows details for the reservation described by this identifier.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'capacity_commitment',
        None,
        'Shows details for the capacity commitment described by this '
        'identifier.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation_assignment',
        None,
        'Looks up reservation assignments for a specified '
        'project/folder/organization. Explicit reservation assignments will be '
        'returned if exist. Otherwise implicit reservation assignments from '
        'parents will be returned. '
        'Used in conjunction with --job_type, --assignee_type and '
        '--assignee_id.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation_group',
        None,
        'Shows details for the reservation group described by this identifier.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'job_type',
        None,
        [
            'QUERY',
            'PIPELINE',
            'ML_EXTERNAL',
            'BACKGROUND',
            'SPARK',
            'CONTINUOUS',
            'BACKGROUND_CHANGE_DATA_CAPTURE',
            'BACKGROUND_COLUMN_METADATA_INDEX',
            'BACKGROUND_SEARCH_INDEX_REFRESH',
        ],
        (
            'Type of jobs to search reservation assignment for. Options'
            ' include:'
            '\n QUERY'
            '\n PIPELINE'
            '\n ML_EXTERNAL'
            '\n BACKGROUND'
            '\n SPARK'
            '\n CONTINUOUS'
            '\n BACKGROUND_CHANGE_DATA_CAPTURE'
            '\n BACKGROUND_COLUMN_METADATA_INDEX'
            '\n BACKGROUND_SEARCH_INDEX_REFRESH'
            '\n Used in conjunction with --reservation_assignment.'
        ),
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'assignee_type',
        None,
        ['PROJECT', 'FOLDER', 'ORGANIZATION'],
        'Type of assignees for the reservation assignment. Options include:'
        '\n PROJECT'
        '\n FOLDER'
        '\n ORGANIZATION'
        '\n Used in conjunction with --reservation_assignment.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'assignee_id',
        None,
        'Project/folder/organization ID, to which the reservation is assigned. '
        'Used in conjunction with --reservation_assignment.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'connection',
        None,
        'Shows details for the connection described by this identifier.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'dataset_view',
        None,
        ['METADATA', 'ACL', 'FULL'],
        'Specifies the view that determines which dataset information is '
        'returned. By default, metadata and ACL information are returned. '
        'Options include:'
        '\n METADATA'
        '\n ACL'
        '\n FULL'
        '\n If not set, defaults as FULL',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'migration_workflow',
        None,
        'Show details of migration workflow described by this identifier.',
        flag_values=fv,
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str = '') -> Optional[int]:
    """Show all information about an object.

    Examples:
      bq show -j <job_id>
      bq show dataset
      bq show [--schema] dataset.table
      bq show [--view] dataset.view
      bq show [--materialized_view] dataset.materialized_view
      bq show -m ds.model
      bq show --routine ds.routine
      bq show --transfer_config projects/p/locations/l/transferConfigs/c
      bq show --transfer_run projects/p/locations/l/transferConfigs/c/runs/r
      bq show --encryption_service_account
      bq show --connection --project_id=project --location=us connection
      bq show --capacity_commitment project:US.capacity_commitment_id
      bq show --reservation --location=US --project_id=project reservation_name
      bq show --reservation_assignment --project_id=project --location=US
          --assignee_type=PROJECT --assignee_id=myproject --job_type=QUERY
      bq show --reservation_assignment --project_id=project --location=US
          --assignee_type=FOLDER --assignee_id=123 --job_type=QUERY
      bq show --reservation_assignment --project_id=project --location=US
          --assignee_type=ORGANIZATION --assignee_id=456 --job_type=QUERY
      bq show --reservation_group --location=US --project_id=project
          reservation_group_name
      bq show --migration_workflow projects/p/locations/l/workflows/workflow_id

    Arguments:
      identifier: the identifier of the resource to show.
    """
    # pylint: disable=g-doc-exception
    client = bq_cached_client.Client.Get()
    custom_format = 'show'
    object_info = None
    print_reference = True
    if self.j:
      reference = bq_client_utils.GetJobReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
      )
    elif self.d:
      self.PossiblyDelegateToGcloudAndExit('datasets', 'show', identifier)
      reference = bq_client_utils.GetDatasetReference(
          id_fallbacks=client, identifier=identifier
      )
      object_info = client_dataset.GetDataset(
          apiclient=client.apiclient,
          reference=reference,
          dataset_view=self.dataset_view,
      )
    elif self.view:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
      custom_format = 'view'
    elif self.materialized_view:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
      custom_format = 'materialized_view'
    elif self.table_replica:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
      custom_format = 'table_replica'
    elif self.schema:
      if bq_flags.FORMAT.value not in [None, 'prettyjson', 'json']:
        raise app.UsageError(
            'Table schema output format must be json or prettyjson.'
        )
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
      custom_format = 'schema'
    elif self.transfer_config:
      formatted_identifier = frontend_id_utils.FormatDataTransferIdentifiers(
          client, identifier
      )
      reference = TransferConfigReference(
          transferConfigName=formatted_identifier
      )
      object_info = client_data_transfer.get_transfer_config(
          client.GetTransferV1ApiClient(), formatted_identifier
      )
    elif self.transfer_run:
      formatted_identifier = frontend_id_utils.FormatDataTransferIdentifiers(
          client, identifier
      )
      reference = TransferRunReference(transferRunName=formatted_identifier)
      object_info = client_data_transfer.get_transfer_run(
          client.GetTransferV1ApiClient(), formatted_identifier
      )
    elif self.m:
      reference = bq_client_utils.GetModelReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.routine:
      reference = bq_client_utils.GetRoutineReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.reservation:
      reference = bq_client_utils.GetReservationReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
      )
      object_info = client_reservation.GetReservation(
          client=client.GetReservationApiClient(), reference=reference
      )
    elif self.reservation_assignment:
      search_all_projects = True
      if search_all_projects:
        object_info = client_reservation.SearchAllReservationAssignments(
            client=client.GetReservationApiClient(),
            location=bq_flags.LOCATION.value,
            job_type=self.job_type,
            assignee_type=self.assignee_type,
            assignee_id=self.assignee_id,
        )
      # Here we just need any object of ReservationAssignmentReference type, but
      # the value of the object doesn't matter here.
      # PrintObjectInfo() will use the type and object_info to format the
      # output.
      reference = ApiClientHelper.ReservationAssignmentReference.Create(
          projectId=' ',
          location=' ',
          reservationId=' ',
          reservationAssignmentId=' ',
      )
      print_reference = False
    elif self.capacity_commitment:
      reference = bq_client_utils.GetCapacityCommitmentReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
      )
      object_info = client_reservation.GetCapacityCommitment(
          client=client.GetReservationApiClient(),
          reference=reference,
      )
    elif self.reservation_group:
      try:
        reference = bq_client_utils.GetReservationGroupReference(
            id_fallbacks=client,
            identifier=identifier,
            default_location=bq_flags.LOCATION.value,
        )
        object_info = client_reservation.GetReservationGroup(
            reservation_group_client=client.GetReservationApiClient(),
            reference=reference,
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to get reservation group '%s': %s" % (identifier, e)
        )
    elif self.encryption_service_account:
      object_info = (
          client.apiclient.projects()
          .getServiceAccount(
              projectId=bq_client_utils.GetProjectReference(
                  id_fallbacks=client
              ).projectId
          )
          .execute()
      )
      email = object_info['email']
      object_info = {'ServiceAccountID': email}
      reference = EncryptionServiceAccount(serviceAccount='serviceAccount')
    elif self.connection:
      reference = bq_client_utils.GetConnectionReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
      )
      object_info = client_connection.GetConnection(
          client=client.GetConnectionV1ApiClient(), reference=reference
      )
    elif self.migration_workflow:
      reference = None
      self.DelegateToGcloudAndExit(
          'migration_workflows',
          'show',
          identifier,
      )

    else:
      reference = bq_client_utils.GetReference(
          id_fallbacks=client, identifier=identifier
      )
    if reference is None:
      raise app.UsageError('Must provide an identifier for show.')

    if isinstance(reference, DatasetReference) and not object_info:
      self.PossiblyDelegateToGcloudAndExit('datasets', 'show', identifier)
      object_info = client_dataset.GetDataset(
          apiclient=client.apiclient,
          reference=reference,
          dataset_view=self.dataset_view,
      )
      pass

    if object_info is None:
      object_info = client_deprecated.get_object_info(
          apiclient=client.apiclient,
          get_routines_api_client=client.GetRoutinesApiClient,
          get_models_api_client=client.GetModelsApiClient,
          reference=reference,
      )
    bq_frontend_utils.PrintObjectInfo(
        object_info,
        reference,
        custom_format=custom_format,
        print_reference=print_reference,
    )
