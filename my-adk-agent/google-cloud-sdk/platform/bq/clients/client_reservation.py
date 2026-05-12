#!/usr/bin/env python
"""The BigQuery CLI reservation client library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import Any, Dict, NamedTuple, Optional, Set, Tuple

from googleapiclient import discovery

from clients import utils as bq_client_utils
from frontend import utils as frontend_utils
from utils import bq_error
from utils import bq_id_utils


def GetBodyForCreateReservation(
    api_version: str,  # pylint: disable=unused-argument Cleanup is error prone.
    slots: int,
    ignore_idle_slots: bool,
    edition,
    target_job_concurrency: Optional[int],
    multi_region_auxiliary: Optional[bool],
    autoscale_max_slots: Optional[int] = None,
    max_slots: Optional[int] = None,
    scaling_mode: Optional[str] = None,
    reservation_group_name: Optional[str] = None,
    scheduling_policy_concurrency: Optional[int] = None,
    scheduling_policy_max_slots: Optional[int] = None,
) -> Dict[str, Any]:
  """Return the request body for CreateReservation.

  Arguments:
    api_version: The api version to make the request against.
    slots: Number of slots allocated to this reservation subtree.
    ignore_idle_slots: Specifies whether queries should ignore idle slots from
      other reservations.
    edition: The edition for this reservation.
    target_job_concurrency: Job concurrency target.
    multi_region_auxiliary: Whether this reservation is for the auxiliary
      region.
    autoscale_max_slots: Number of slots to be scaled when needed.
    max_slots: The overall max slots for the reservation.
    scaling_mode: The scaling mode for the reservation.
    reservation_group_name: The reservation group name which the reservation
      belongs to.
    scheduling_policy_concurrency: Soft cap on project concurrency within the
      reservation.
    scheduling_policy_max_slots: Soft cap on project max slots within the
      reservation.

  Returns:
    Reservation object that was created.

  Raises:
    bq_error.BigqueryError: if requirements for parameters are not met.
  """
  reservation = {}
  reservation['slot_capacity'] = slots
  reservation['ignore_idle_slots'] = ignore_idle_slots
  if multi_region_auxiliary is not None:
    reservation['multi_region_auxiliary'] = multi_region_auxiliary
  if target_job_concurrency is not None:
    reservation['concurrency'] = target_job_concurrency

  if autoscale_max_slots is not None:
    reservation['autoscale'] = {}
    reservation['autoscale']['max_slots'] = autoscale_max_slots

  if edition is not None:
    reservation['edition'] = edition

  if frontend_utils.ValidateAtMostOneSelected(max_slots, autoscale_max_slots):
    raise bq_error.BigqueryError(
        'max_slots and autoscale_max_slots cannot be set at the same time.'
    )
  # make sure max_slots and scaling_mode are set at the same time.
  if (max_slots is not None and scaling_mode is None) or (
      max_slots is None and scaling_mode is not None
  ):
    raise bq_error.BigqueryError(
        'max_slots and scaling_mode must be set at the same time.'
    )

  if max_slots is not None:
    reservation['max_slots'] = max_slots
  if scaling_mode is not None:
    reservation['scaling_mode'] = scaling_mode

  if reservation_group_name is not None:
    reservation['reservation_group'] = reservation_group_name

  if scheduling_policy_concurrency is not None:
    reservation['scheduling_policy'] = {}
    reservation['scheduling_policy'][
        'concurrency'
    ] = scheduling_policy_concurrency
  if scheduling_policy_max_slots is not None:
    if 'scheduling_policy' not in reservation:
      reservation['scheduling_policy'] = {}
    reservation['scheduling_policy']['max_slots'] = scheduling_policy_max_slots

  return reservation


def GetBodyForCreateReservationAssignment(
    reference: str,  # pylint: disable=unused-argument Cleanup is error prone.
    job_type: Optional[str],
    priority: Optional[str],
    assignee_type: str,
    assignee_id: str,
    scheduling_policy_max_slots: Optional[int] = None,
    scheduling_policy_concurrency: Optional[int] = None,
) -> Dict[str, Any]:
  """Creates a reservation assignment for a given project/folder/organization.

  Arguments:
    reference: Reference to the project reservation is assigned. Location must
      be the same location as the reservation.
    job_type: Type of jobs for this assignment.
    priority: Default job priority for this assignment.
    assignee_type: Type of assignees for the reservation assignment.
    assignee_id: Project/folder/organization ID, to which the reservation is
      assigned.
    scheduling_policy_max_slots: Max slots for the scheduling policy.
    scheduling_policy_concurrency: Concurrency for the scheduling policy.

  Returns:
    ReservationAssignment object that was created.

  Raises:
    bq_error.BigqueryError: if assignment cannot be created.
  """
  reservation_assignment = {}
  if not job_type:
    raise_job_type_unspecified_error = True
    if (
        scheduling_policy_max_slots is not None
        or scheduling_policy_concurrency is not None
    ):
      raise_job_type_unspecified_error = False
    if raise_job_type_unspecified_error:
      raise bq_error.BigqueryError('job_type not specified.')
  else:
    reservation_assignment['job_type'] = job_type
  if priority:
    reservation_assignment['priority'] = priority
  if not assignee_type:
    raise bq_error.BigqueryError('assignee_type not specified.')
  if not assignee_id:
    raise bq_error.BigqueryError('assignee_id not specified.')
  # assignee_type is singular, that's why we need additional 's' inside
  # format string for assignee below.
  reservation_assignment['assignee'] = '%ss/%s' % (
      assignee_type.lower(),
      assignee_id,
  )
  if scheduling_policy_max_slots is not None:
    if 'scheduling_policy' not in reservation_assignment:
      reservation_assignment['scheduling_policy'] = {}
    reservation_assignment['scheduling_policy'][
        'max_slots'
    ] = scheduling_policy_max_slots
  if scheduling_policy_concurrency is not None:
    if 'scheduling_policy' not in reservation_assignment:
      reservation_assignment['scheduling_policy'] = {}
    reservation_assignment['scheduling_policy'][
        'concurrency'
    ] = scheduling_policy_concurrency

  return reservation_assignment


def CreateReservation(
    client,
    api_version: str,
    reference,
    slots: int,
    ignore_idle_slots: bool,
    edition,
    target_job_concurrency: Optional[int],
    multi_region_auxiliary: Optional[bool],
    autoscale_max_slots: Optional[int] = None,
    max_slots: Optional[int] = None,
    scaling_mode: Optional[str] = None,
    reservation_group_name: Optional[str] = None,
    scheduling_policy_concurrency: Optional[int] = None,
    scheduling_policy_max_slots: Optional[int] = None,
) -> Dict[str, Any]:
  """Create a reservation with the given reservation reference.

  Arguments:
    client: The client used to make the request.
    api_version: The api version to make the request against.
    reference: Reservation to create.
    slots: Number of slots allocated to this reservation subtree.
    ignore_idle_slots: Specifies whether queries should ignore idle slots from
      other reservations.
    edition: The edition for this reservation.
    target_job_concurrency: Job concurrency target.
    multi_region_auxiliary: Whether this reservation is for the auxiliary
      region.
    autoscale_max_slots: Number of slots to be scaled when needed.
    max_slots: The overall max slots for the reservation.
    scaling_mode: The scaling mode for the reservation.
    reservation_group_name: The reservation group name which the reservation
      belongs to.

  Returns:
    Reservation object that was created.

  Raises:
    bq_error.BigqueryError: if autoscale_max_slots is used with other
      version.
  """
  reservation = GetBodyForCreateReservation(
      api_version,
      slots,
      ignore_idle_slots,
      edition,
      target_job_concurrency,
      multi_region_auxiliary,
      autoscale_max_slots,
      max_slots,
      scaling_mode,
      reservation_group_name,
      scheduling_policy_concurrency,
      scheduling_policy_max_slots,
  )
  parent = 'projects/%s/locations/%s' % (
      reference.projectId,
      reference.location,
  )
  return (
      client.projects()
      .locations()
      .reservations()
      .create(
          parent=parent, body=reservation, reservationId=reference.reservationId
      )
      .execute()
  )


def ListReservations(
    client,
    reference,
    page_size: int,
    page_token: Optional[str],
    reservation_group: Optional[str] = None,
) -> Any:
  """List reservations in the project and location for the given reference.

  Arguments:
    client: The client used to make the request.
    reference: Reservation reference containing project and location.
    page_size: Number of results to show.
    page_token: Token to retrieve the next page of results.
    reservation_group: When specified, only list reservations in the given
      reservation group.

  Returns:
    Reservation object that was created.
  """
  parent = 'projects/%s/locations/%s' % (
      reference.projectId,
      reference.location,
  )
  if reservation_group is not None:
    return (
        client.projects()
        .locations()
        .reservations()
        .list(
            parent=parent,
            pageSize=page_size,
            pageToken=page_token,
            filter='reservation_group=%s' % reservation_group,
        )
        .execute()
    )
  return (
      client.projects()
      .locations()
      .reservations()
      .list(parent=parent, pageSize=page_size, pageToken=page_token)
      .execute()
  )


def ListBiReservations(client, reference):
  """List BI reservations in the project and location for the given reference.

  Arguments:
    client: The client used to make the request.
    reference: Reservation reference containing project and location.

  Returns:
    List of BI reservations in the given project/location.
  """
  parent = 'projects/%s/locations/%s/biReservation' % (
      reference.projectId,
      reference.location,
  )
  response = (
      client.projects().locations().getBiReservation(name=parent).execute()
  )
  return response


def GetReservation(client, reference):
  """Gets a reservation with the given reservation reference.

  Arguments:
    client: The client used to make the request.
    reference: Reservation to get.

  Returns:
    Reservation object corresponding to the given id.
  """
  return (
      client.projects()
      .locations()
      .reservations()
      .get(name=reference.path())
      .execute()
  )


def DeleteReservation(
    client,
    reference
):
  """Deletes a reservation with the given reservation reference.

  Arguments:
    client: The client used to make the request.
    reference: Reservation to delete.
  """
  client.projects().locations().reservations().delete(
      name=reference.path()
  ).execute()


def UpdateBiReservation(client, reference, reservation_size: str):
  """Updates a BI reservation with the given reservation reference.

  Arguments:
    client: The client used to make the request.
    reference: Reservation to update.
    reservation_size: size of reservation in GBs. It may only contain digits,
      optionally followed by 'G', 'g', 'GB, 'gb', 'gB', or 'Gb'.

  Returns:
    Reservation object that was updated.
  Raises:
    ValueError: if reservation_size is malformed.
  """

  if (
      reservation_size.upper().endswith('GB')
      and reservation_size[:-2].isdigit()
  ):
    reservation_digits = reservation_size[:-2]
  elif (
      reservation_size.upper().endswith('G') and reservation_size[:-1].isdigit()
  ):
    reservation_digits = reservation_size[:-1]
  elif reservation_size.isdigit():
    reservation_digits = reservation_size
  else:
    raise ValueError("""Invalid reservation size. The unit for BI reservations
    is GB. The specified reservation size may only contain digits, optionally
    followed by G, g, GB, gb, gB, or Gb.""")

  reservation_size = int(reservation_digits) * 1024 * 1024 * 1024

  bi_reservation = {}
  update_mask = ''
  bi_reservation['size'] = reservation_size
  update_mask += 'size,'
  return (
      client.projects()
      .locations()
      .updateBiReservation(
          name=reference.path(), updateMask=update_mask, body=bi_reservation
      )
      .execute()
  )




def GetParamsForUpdateReservation(
    client,
    reference,
    api_version: str,  # pylint: disable=unused-argument Cleanup is error prone.
    slots: int,
    ignore_idle_slots: bool,
    target_job_concurrency: Optional[int],
    autoscale_max_slots: Optional[int] = None,
    max_slots: Optional[int] = None,
    scaling_mode: Optional[str] = None,
    labels_to_set: Optional[Dict[str, str]] = None,
    label_keys_to_remove: Optional[Set[str]] = None,
    reservation_group_name: Optional[str] = None,
    scheduling_policy_concurrency: Optional[int] = None,
    scheduling_policy_max_slots: Optional[int] = None,
) -> Tuple[Dict[str, Any], str]:
  """Return the request body and update mask for UpdateReservation.

  Arguments:
    api_version: The api version to make the request against.
    slots: Number of slots allocated to this reservation subtree.
    ignore_idle_slots: Specifies whether queries should ignore idle slots from
      other reservations.
    target_job_concurrency: Job concurrency target.
    autoscale_max_slots: Number of slots to be scaled when needed.
    max_slots: The overall max slots for the reservation.
    scaling_mode: The scaling mode for the reservation.
    reservation_group_name: The reservation group name that the reservation
      belongs to.
    scheduling_policy_concurrency: Soft cap on project concurrency within the
      reservation.
    scheduling_policy_max_slots: Soft cap on project max slots within the
      reservation.

  Returns:
    Reservation object that was updated.

  Raises:
    bq_error.BigqueryError: if parameters are incompatible.
  """
  reservation = {}
  update_mask = ''
  if slots is not None:
    reservation['slot_capacity'] = slots
    update_mask += 'slot_capacity,'

  if ignore_idle_slots is not None:
    reservation['ignore_idle_slots'] = ignore_idle_slots
    update_mask += 'ignore_idle_slots,'

  if target_job_concurrency is not None:
    reservation['concurrency'] = target_job_concurrency
    update_mask += 'concurrency,'

  if autoscale_max_slots is not None:
    if autoscale_max_slots != 0:
      reservation['autoscale'] = {}
      reservation['autoscale']['max_slots'] = autoscale_max_slots
      update_mask += 'autoscale.max_slots,'
    else:
      # Disable autoscale.
      update_mask += 'autoscale,'

  if label_keys_to_remove is not None or labels_to_set is not None:
    lookup_reservation = GetReservation(client, reference)
    if 'labels' in lookup_reservation:
      reservation['labels'] = lookup_reservation['labels']
    else:
      reservation['labels'] = {}
    update_mask += 'labels,'

  if label_keys_to_remove is not None:
    for key in label_keys_to_remove:
      if key in reservation['labels']:
        del reservation['labels'][key]

  if labels_to_set is not None:
    for key, value in labels_to_set.items():
      reservation['labels'][key] = value

  if frontend_utils.ValidateAtMostOneSelectedAllowsDefault(
      max_slots, autoscale_max_slots
  ):
    raise bq_error.BigqueryError(
        'max_slots and autoscale_max_slots cannot be set at the same time.'
    )

  # Not we don't need to perform the following check for creation,
  # because there we check the co-existence of max_slots and scaling_mode, so
  # we just need to make sure max_slots and autoscale_max_slots doesn't occur
  # at the same time.
  if (scaling_mode is not None and autoscale_max_slots is not None) and (
      scaling_mode != 'SCALING_MODE_UNSPECIFIED' and autoscale_max_slots != 0
  ):
    raise bq_error.BigqueryError(
        'scaling_mode and autoscale_max_slots cannot be set at the same time.'
    )

  # Note: for update we don't require max_slots and scaling_mode being changed
  # set at the same time.
  # Although backend should make sure them to work together.

  if max_slots is not None:
    reservation['max_slots'] = max_slots
    update_mask += 'max_slots,'
  if scaling_mode is not None:
    reservation['scaling_mode'] = scaling_mode
    update_mask += 'scaling_mode,'

  if reservation_group_name is not None:
    reservation['reservation_group'] = reservation_group_name
    update_mask += 'reservation_group,'

  if scheduling_policy_concurrency is not None:
    reservation['scheduling_policy'] = {}
    reservation['scheduling_policy'][
        'concurrency'
    ] = scheduling_policy_concurrency
    update_mask += 'scheduling_policy.concurrency,'

  if scheduling_policy_max_slots is not None:
    if 'scheduling_policy' not in reservation:
      reservation['scheduling_policy'] = {}
    reservation['scheduling_policy']['max_slots'] = scheduling_policy_max_slots
    update_mask += 'scheduling_policy.max_slots,'

  return reservation, update_mask


def UpdateReservation(
    client,
    api_version: str,
    reference,
    slots,
    ignore_idle_slots,
    target_job_concurrency: Optional[int],
    autoscale_max_slots: Optional[int] = None,
    max_slots: Optional[int] = None,
    scaling_mode: Optional[str] = None,
    labels_to_set: Optional[Dict[str, str]] = None,
    label_keys_to_remove: Optional[Set[str]] = None,
    reservation_group_name: Optional[str] = None,
    scheduling_policy_concurrency: Optional[int] = None,
    scheduling_policy_max_slots: Optional[int] = None,
):
  """Updates a reservation with the given reservation reference.

  Arguments:
    client: The client used to make the request.
    api_version: The api version to make the request against.
    reference: Reservation to update.
    slots: Number of slots allocated to this reservation subtree.
    ignore_idle_slots: Specifies whether queries should ignore idle slots from
      other reservations.
    target_job_concurrency: Job concurrency target.
    autoscale_max_slots: Number of slots to be scaled when needed.
    max_slots: The overall max slots for the reservation.
    scaling_mode: The scaling mode for the reservation.
    reservation_group_name: The reservation group name that the reservation
      belongs to.
    scheduling_policy_concurrency: Soft cap on project concurrency within the
      reservation.
    scheduling_policy_max_slots: Soft cap on project max slots within the
      reservation.

  Returns:
    Reservation object that was updated.

  Raises:
    bq_error.BigqueryError: if autoscale_max_slots is used with other
      version.
  """
  reservation, update_mask = GetParamsForUpdateReservation(
      client,
      reference,
      api_version,
      slots,
      ignore_idle_slots,
      target_job_concurrency,
      autoscale_max_slots,
      max_slots,
      scaling_mode,
      labels_to_set,
      label_keys_to_remove,
      reservation_group_name,
      scheduling_policy_concurrency,
      scheduling_policy_max_slots,
  )
  return (
      client.projects()
      .locations()
      .reservations()
      .patch(name=reference.path(), updateMask=update_mask, body=reservation)
      .execute()
  )


def CreateCapacityCommitment(
    client,
    reference,
    edition,
    slots: int,
    plan: str,
    renewal_plan: str,
    multi_region_auxiliary: Optional[bool],
) -> Dict[str, Any]:
  """Create a capacity commitment.

  Arguments:
    client: The client used to make the request.
    reference: Project to create a capacity commitment within.
    edition: The edition for this capacity commitment.
    slots: Number of slots in this commitment.
    plan: Commitment plan for this capacity commitment.
    renewal_plan: Renewal plan for this capacity commitment.
    multi_region_auxiliary: Whether this commitment is for the auxiliary region.

  Returns:
    Capacity commitment object that was created.
  """
  capacity_commitment = {}
  capacity_commitment['slot_count'] = slots
  capacity_commitment['plan'] = plan
  capacity_commitment['renewal_plan'] = renewal_plan
  if multi_region_auxiliary is not None:
    capacity_commitment['multi_region_auxiliary'] = multi_region_auxiliary
  if edition is not None:
    capacity_commitment['edition'] = edition
  parent = 'projects/%s/locations/%s' % (
      reference.projectId,
      reference.location,
  )
  capacity_commitment_id = None
  if reference.capacityCommitmentId and reference.capacityCommitmentId != ' ':
    capacity_commitment_id = reference.capacityCommitmentId
  request = (
      client.projects()
      .locations()
      .capacityCommitments()
      .create(
          parent=parent,
          body=capacity_commitment,
          capacityCommitmentId=capacity_commitment_id,
      )
  )
  return request.execute()


def ListCapacityCommitments(client, reference, page_size, page_token):
  """Lists capacity commitments for given project and location.

  Arguments:
    client: The client used to make the request.
    reference: Reference to the project and location.
    page_size: Number of results to show.
    page_token: Token to retrieve the next page of results.

  Returns:
    list of CapacityCommitments objects.
  """
  parent = 'projects/%s/locations/%s' % (
      reference.projectId,
      reference.location,
  )
  return (
      client.projects()
      .locations()
      .capacityCommitments()
      .list(parent=parent, pageSize=page_size, pageToken=page_token)
      .execute()
  )


def GetCapacityCommitment(client, reference):
  """Gets a capacity commitment with the given capacity commitment reference.

  Arguments:
    client: The client used to make the request.
    reference: Capacity commitment to get.

  Returns:
    Capacity commitment object corresponding to the given id.
  """
  return (
      client.projects()
      .locations()
      .capacityCommitments()
      .get(name=reference.path())
      .execute()
  )


def DeleteCapacityCommitment(client, reference, force=None):
  """Deletes a capacity commitment with the given capacity commitment reference.

  Arguments:
    client: The client used to make the request.
    reference: Capacity commitment to delete.
    force: Force delete capacity commitment, ignoring commitment end time.
  """
  client.projects().locations().capacityCommitments().delete(
      name=reference.path(), force=force
  ).execute()


def UpdateCapacityCommitment(client, reference, plan, renewal_plan):
  """Updates a capacity commitment with the given reference.

  Arguments:
    client: The client used to make the request.
    reference: Capacity commitment to update.
    plan: Commitment plan for this capacity commitment.
    renewal_plan: Renewal plan for this capacity commitment.

  Returns:
    Capacity commitment object that was updated.

  Raises:
    bq_error.BigqueryError: if capacity commitment cannot be updated.
  """
  if plan is None and renewal_plan is None:
    raise bq_error.BigqueryError('Please specify fields to be updated.')
  capacity_commitment = {}
  update_mask = []
  if plan is not None:
    capacity_commitment['plan'] = plan
    update_mask.append('plan')
  if renewal_plan is not None:
    capacity_commitment['renewal_plan'] = renewal_plan
    update_mask.append('renewal_plan')

  return (
      client.projects()
      .locations()
      .capacityCommitments()
      .patch(
          name=reference.path(),
          updateMask=','.join(update_mask),
          body=capacity_commitment,
      )
      .execute()
  )


def SplitCapacityCommitment(
    client,
    reference,
    slots,
):
  """Splits a capacity commitment with the given reference into two.

  Arguments:
    client: The client used to make the request.
    reference: Capacity commitment to split.
    slots: Number of slots in the first capacity commitment after the split.

  Returns:
    List of capacity commitment objects after the split.

  Raises:
    bq_error.BigqueryError: if capacity commitment cannot be updated.
  """
  if slots is None:
    raise bq_error.BigqueryError('Please specify slots for the split.')
  body = {'slotCount': slots}
  response = (
      client.projects()
      .locations()
      .capacityCommitments()
      .split(name=reference.path(), body=body)
      .execute()
  )
  if 'first' not in response or 'second' not in response:
    raise bq_error.BigqueryError('internal error')
  return [response['first'], response['second']]


def MergeCapacityCommitments(
    client, project_id, location, capacity_commitment_ids
):
  """Merges capacity commitments into one.

  Arguments:
    client: The client used to make the request.
    project_id: The project ID of the resources to update.
    location: Capacity commitments location.
    capacity_commitment_ids: List of capacity commitment ids.

  Returns:
    Merged capacity commitment.

  Raises:
    bq_error.BigqueryError: if capacity commitment cannot be merged.
  """
  if not project_id:
    raise bq_error.BigqueryError('project id must be specified.')
  if not location:
    raise bq_error.BigqueryError('location must be specified.')
  if capacity_commitment_ids is None or len(capacity_commitment_ids) < 2:
    raise bq_error.BigqueryError(
        'at least 2 capacity commitments must be specified.'
    )
  parent = 'projects/%s/locations/%s' % (project_id, location)
  body = {'capacityCommitmentIds': capacity_commitment_ids}
  return (
      client.projects()
      .locations()
      .capacityCommitments()
      .merge(parent=parent, body=body)
      .execute()
  )


def CreateReservationAssignment(
    client,
    reference,
    assignee_type: Optional[str] = None,
    assignee_id: Optional[str] = None,
    job_type: Optional[str] = None,
    priority: Optional[str] = None,
    scheduling_policy_max_slots: Optional[int] = None,
    scheduling_policy_concurrency: Optional[int] = None,
):
  """Creates a reservation assignment for a given project/folder/organization.

  Arguments:
    client: The client used to make the request.
    reference: Reference to the project reservation is assigned. Location must
      be the same location as the reservation.
    assignee_type: Type of assignees for the reservation assignment.
    assignee_id: Project/folder/organization ID, to which the reservation is
      assigned.
    job_type: Type of jobs for this assignment.
    priority: Default job priority for this assignment.
    scheduling_policy_max_slots: Soft cap on max slots for a specific project
      within the reservation.
    scheduling_policy_concurrency: Soft cap on job concurrency for a specific
      project within the reservation.

  Returns:
    ReservationAssignment object that was created.

  Raises:
    bq_error.BigqueryError: if assignment cannot be created.
  """
  reservation_assignment = GetBodyForCreateReservationAssignment(
      reference,
      job_type,
      priority,
      assignee_type,
      assignee_id,
      scheduling_policy_max_slots,
      scheduling_policy_concurrency,
  )

  return (
      client.projects()
      .locations()
      .reservations()
      .assignments()
      .create(parent=reference.path(), body=reservation_assignment)
      .execute()
  )


def DeleteReservationAssignment(client, reference):
  """Deletes given reservation assignment.

  Arguments:
    client: The client used to make the request.
    reference: Reference to the reservation assignment.
  """
  client.projects().locations().reservations().assignments().delete(
      name=reference.path()
  ).execute()


def MoveReservationAssignment(
    client,
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('api_version', Optional[str]),
        ],
    ),
    reference,
    destination_reservation_id,
    default_location,
):
  """Moves given reservation assignment under another reservation."""
  destination_reservation_reference = bq_client_utils.GetReservationReference(
      id_fallbacks=id_fallbacks,
      identifier=destination_reservation_id,
      default_location=default_location,
      check_reservation_project=False,
  )
  body = {'destinationId': destination_reservation_reference.path()}

  return (
      client.projects()
      .locations()
      .reservations()
      .assignments()
      .move(name=reference.path(), body=body)
      .execute()
  )


def UpdateReservationAssignment(
    client,
    reference,
    priority,
    scheduling_policy_max_slots,
    scheduling_policy_concurrency,
):
  """Updates reservation assignment.

  Arguments:
    client: The client used to make the request.
    reference: Reference to the reservation assignment.
    priority: Default job priority for this assignment.
    scheduling_policy_max_slots: Max slots for the scheduling policy.
    scheduling_policy_concurrency: Concurrency for the scheduling policy.

  Returns:
    Reservation assignment object that was updated.

  Raises:
    bq_error.BigqueryError: if assignment cannot be updated.
  """
  reservation_assignment = {}
  update_mask = ''
  if priority is not None:
    if not priority:
      priority = 'JOB_PRIORITY_UNSPECIFIED'
    reservation_assignment['priority'] = priority
    update_mask += 'priority,'
  if scheduling_policy_max_slots is not None:
    reservation_assignment['scheduling_policy'] = {}
    reservation_assignment['scheduling_policy'][
        'max_slots'
    ] = scheduling_policy_max_slots
    update_mask += 'scheduling_policy.max_slots,'
  if scheduling_policy_concurrency is not None:
    if 'scheduling_policy' not in reservation_assignment:
      reservation_assignment['scheduling_policy'] = {}
    reservation_assignment['scheduling_policy'][
        'concurrency'
    ] = scheduling_policy_concurrency
    update_mask += 'scheduling_policy.concurrency,'
  return (
      client.projects()
      .locations()
      .reservations()
      .assignments()
      .patch(
          name=reference.path(),
          updateMask=update_mask,
          body=reservation_assignment,
      )
      .execute()
  )


def ListReservationAssignments(client, reference, page_size, page_token):
  """Lists reservation assignments for given project and location.

  Arguments:
    client: The client used to make the request.
    reference: Reservation reference for the parent.
    page_size: Number of results to show.
    page_token: Token to retrieve the next page of results.

  Returns:
    ReservationAssignment object that was created.
  """
  return (
      client.projects()
      .locations()
      .reservations()
      .assignments()
      .list(parent=reference.path(), pageSize=page_size, pageToken=page_token)
      .execute()
  )




def SearchAllReservationAssignments(
    client, location: str, job_type: str, assignee_type: str, assignee_id: str
) -> Dict[str, Any]:
  """Searches reservations assignments for given assignee.

  Arguments:
    client: The client used to make the request.
    location: location of interest.
    job_type: type of job to be queried.
    assignee_type: Type of assignees for the reservation assignment.
    assignee_id: Project/folder/organization ID, to which the reservation is
      assigned.

  Returns:
    ReservationAssignment object if it exists.

  Raises:
    bq_error.BigqueryError: If required parameters are not passed in or
      reservation assignment not found.
  """
  if not location:
    raise bq_error.BigqueryError('location not specified.')
  if not job_type:
    raise bq_error.BigqueryError('job_type not specified.')
  if not assignee_type:
    raise bq_error.BigqueryError('assignee_type not specified.')
  if not assignee_id:
    raise bq_error.BigqueryError('assignee_id not specified.')
  # assignee_type is singular, that's why we need additional 's' inside
  # format string for assignee below.
  assignee = '%ss/%s' % (assignee_type.lower(), assignee_id)
  query = 'assignee=%s' % assignee
  parent = 'projects/-/locations/%s' % location

  response = (
      client.projects()
      .locations()
      .searchAllAssignments(parent=parent, query=query)
      .execute()
  )
  if 'assignments' in response:
    for assignment in response['assignments']:
      if assignment['jobType'] == job_type:
        return assignment
  raise bq_error.BigqueryError('Reservation assignment not found')


def CreateReservationGroup(
    reservation_group_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ReservationGroupReference,
) -> Dict[str, Any]:
  """Creates a reservation group with the given reservation group reference.

  Arguments:
    reservation_group_client: The client used to make the request.
    reference: Reservation group to create.

  Returns:
    Reservation group object that was created.

  Raises:
    bq_error.BigqueryError: if reservation group cannot be created.
  """

  parent = 'projects/%s/locations/%s' % (
      reference.projectId,
      reference.location,
  )
  reservation_group = {}
  return (
      reservation_group_client.projects()
      .locations()
      .reservationGroups()
      .create(
          parent=parent,
          body=reservation_group,
          reservationGroupId=reference.reservationGroupId,
      )
      .execute()
  )




def ListReservationGroups(
    reservation_group_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ReservationGroupReference,
    page_size: int,
    page_token: str,
):
  """Lists reservation groups in the project and location for the given reference.

  Arguments:
    reservation_group_client: The client used to make the request.
    reference: Reservation group reference containing project and location.
    page_size: Number of results to show.
    page_token: Token to retrieve the next page of results.

  Returns:
    Reservation group object that was created.
  """
  parent = 'projects/%s/locations/%s' % (
      reference.projectId,
      reference.location,
  )
  return (
      reservation_group_client.projects()
      .locations()
      .reservationGroups()
      .list(parent=parent, pageSize=page_size, pageToken=page_token)
      .execute()
  )


def GetReservationGroup(
    reservation_group_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ReservationGroupReference,
):
  """Gets a reservation group with the given reservation group reference.

  Arguments:
    reservation_group_client: The client used to make the request.
    reference: Reservation group to get.

  Returns:
    Reservation group object corresponding to the given id.
  """
  return (
      reservation_group_client.projects()
      .locations()
      .reservationGroups()
      .get(name=reference.path())
      .execute()
  )


def DeleteReservationGroup(
    reservation_group_client: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ReservationGroupReference,
):
  """Deletes a reservation group with the given reservation group reference.

  Arguments:
    reservation_group_client: The client used to make the request.
    reference: Reservation group to delete.
  """
  reservation_group_client.projects().locations().reservationGroups().delete(
      name=reference.path()
  ).execute()


def SetReservationIAMPolicy(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ReservationReference,
    policy: str,
):
  """Sets IAM policy for the given reservation resource.

  Arguments:
    apiclient: the apiclient used to make the request.
    reference: the ReservationReference for the reservation resource.
    policy: The policy string in JSON format.

  Returns:
    The updated IAM policy attached to the given reservation resource.

  Raises:
    BigqueryTypeError: if reference is not a ReservationReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ReservationReference,
      method='SetReservationIAMPolicy',
  )
  request = {'policy': policy}
  return (
      apiclient.projects()
      .locations()
      .reservations()
      .setIamPolicy(body=request, resource=reference.path())
      .execute()
  )


def GetReservationIAMPolicy(
    apiclient: discovery.Resource,
    reference: bq_id_utils.ApiClientHelper.ReservationReference,
):
  """Gets IAM policy for the given reservation resource.

  Arguments:
    apiclient: the apiclient used to make the request.
    reference: the ReservationReference for the reservation resource.

  Returns:
    The IAM policy attached to the given reservation resource.

  Raises:
    BigqueryTypeError: if reference is not a ReservationReference.
  """
  bq_id_utils.typecheck(
      reference,
      bq_id_utils.ApiClientHelper.ReservationReference,
      method='GetReservationIAMPolicy',
  )
  return (
      apiclient.projects()
      .locations()
      .reservations()
      .getIamPolicy(resource=reference.path())
      .execute()
  )


