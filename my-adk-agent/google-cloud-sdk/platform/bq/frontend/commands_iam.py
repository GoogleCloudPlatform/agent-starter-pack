#!/usr/bin/env python
"""All the BigQuery CLI IAM commands."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
from typing import Optional

from absl import app
from absl import flags

import bq_flags
import bq_utils
from clients import client_connection
from clients import client_dataset
from clients import client_reservation
from clients import client_routine
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import utils as frontend_utils
from utils import bq_id_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class _IamPolicyCmd(bigquery_command.BigqueryCmd):
  """Common superclass for commands that interact with BQ's IAM meta API.

  Provides common flags, identifier decoding logic, and GetIamPolicy and
  SetIamPolicy logic.
  """

  def __init__(self, name: str, fv: flags.FlagValues, verb):
    """Initialize.

    Args:
      name: the command name string to bind to this handler class.
      fv: the FlagValues flag-registry object.
      verb: the verb string (e.g. 'Set', 'Get', 'Add binding to', ...) to print
        in various descriptions.
    """
    super(_IamPolicyCmd, self).__init__(name, fv)

    # The shell doesn't currently work with commands containing hyphens. That
    # requires some internal rewriting logic.
    self.surface_in_shell = False

    flags.DEFINE_boolean(
        'dataset',
        False,
        '%s IAM policy for dataset described by this identifier.' % verb,
        short_name='d',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'table',
        False,
        '%s IAM policy for table described by this identifier.' % verb,
        short_name='t',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'connection',
        False,
        '%s IAM policy for connection described by this identifier.' % verb,
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'routine',
        False,
        '%s IAM policy for routine described by this identifier.' % verb,
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation',
        False,
        '%s IAM policy for reservation described by this identifier.' % verb,
        flag_values=fv,
    )
    # Subclasses should call self._ProcessCommandRc(fv) after calling this
    # superclass initializer and adding their own flags.

  def GetReferenceFromIdentifier(self, client, identifier):
    # pylint: disable=g-doc-exception
    if frontend_utils.ValidateAtMostOneSelected(
        self.d,
        self.t,
        self.connection,
        self.routine,
        self.reservation,
    ):
      raise app.UsageError(
          'Cannot specify more than one of -d, -t, --routine, --connection,'
          ' --reservation'
          '.'
      )

    if not identifier:
      raise app.UsageError(
          'Must provide an identifier for %s.' % (self._command_name,)
      )

    if self.t:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.d:
      reference = bq_client_utils.GetDatasetReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.connection:
      reference = bq_client_utils.GetConnectionReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
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
    else:
      reference = bq_client_utils.GetReference(
          id_fallbacks=client, identifier=identifier
      )
      bq_id_utils.typecheck(
          reference,
          (
              bq_id_utils.ApiClientHelper.DatasetReference,
              bq_id_utils.ApiClientHelper.TableReference,
              bq_id_utils.ApiClientHelper.RoutineReference,
              bq_id_utils.ApiClientHelper.ReservationReference,
          ),
          'Invalid identifier "%s" for %s.' % (identifier, self._command_name),
          is_usage_error=True,
      )
    return reference

  def GetPolicyForReference(self, client, reference):
    """Get the IAM policy for a table, dataset, routine or reservation.

    Args:
      reference: A DatasetReference, TableReference, ConnectionReference,
        RoutineReference, or ReservationReference.

    Returns:
      The policy object, composed of dictionaries, lists, and primitive types.

    Raises:
      RuntimeError: reference isn't an expected type.
    """
    if isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
      return client_table.get_table_iam_policy(
          iampolicy_client=client.GetIAMPolicyApiClient(), reference=reference
      )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.DatasetReference):
      return client_dataset.GetDatasetIAMPolicy(
          apiclient=client.GetIAMPolicyApiClient(), reference=reference
      )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.ConnectionReference):
      return client_connection.GetConnectionIAMPolicy(
          client=client.GetConnectionV1ApiClient(), reference=reference
      )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.RoutineReference):
      return client_routine.GetRoutineIAMPolicy(
          apiclient=client.GetIAMPolicyApiClient(), reference=reference
      )
    elif isinstance(
        reference, bq_id_utils.ApiClientHelper.ReservationReference
    ):
      return client_reservation.GetReservationIAMPolicy(
          apiclient=client.GetReservationApiClient(), reference=reference
      )
    raise RuntimeError(
        'Unexpected reference type: {r_type}'.format(r_type=type(reference))
    )

  def SetPolicyForReference(self, client, reference, policy):
    """Set the IAM policy for a table, dataset, connection, routine, or reservation.

    Args:
      reference: A DatasetReference, TableReference, ConnectionReference,
        RoutineReference, or ReservationReference.
      policy: The policy object, composed of dictionaries, lists, and primitive
        types.

    Raises:
      RuntimeError: reference isn't an expected type.
    """
    if isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
      return client_table.set_table_iam_policy(
          iampolicy_client=client.GetIAMPolicyApiClient(),
          reference=reference,
          policy=policy,
      )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.DatasetReference):
      return client_dataset.SetDatasetIAMPolicy(
          apiclient=client.GetIAMPolicyApiClient(),
          reference=reference,
          policy=policy,
      )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.ConnectionReference):
      return client_connection.SetConnectionIAMPolicy(
          client=client.GetConnectionV1ApiClient(),
          reference=reference,
          policy=policy,
      )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.RoutineReference):
      return client_routine.SetRoutineIAMPolicy(
          apiclient=client.GetIAMPolicyApiClient(),
          reference=reference,
          policy=policy,
      )
    elif isinstance(
        reference, bq_id_utils.ApiClientHelper.ReservationReference
    ):
      return client_reservation.SetReservationIAMPolicy(
          apiclient=client.GetReservationApiClient(),
          reference=reference,
          policy=policy,
      )
    raise RuntimeError(
        'Unexpected reference type: {r_type}'.format(r_type=type(reference))
    )


class GetIamPolicy(_IamPolicyCmd):  # pylint: disable=missing-docstring
  usage = """get-iam-policy [(-d|-t|-connection|--reservation|-routine)] <identifier>"""
  command = 'get-iam-policy'

  def __init__(self, name: str, fv: flags.FlagValues):
    super().__init__(name, fv, 'Get')
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str) -> Optional[int]:
    """Get the IAM policy for a resource.

    Gets the IAM policy for a dataset, table, routine, connection, or
    reservation resource, and prints it to stdout. The policy is in JSON format.

    Usage:
    get-iam-policy <identifier>

    Examples:
      bq get-iam-policy ds.table1
      bq get-iam-policy --project_id=proj -t ds.table1
      bq get-iam-policy proj:ds.table1
      bq get-iam-policy --reservation proj:ds.reservation1

    Arguments:
      identifier: The identifier of the resource. Presently only table, view,
        connection, and reservation resources are fully supported. (Last
        updated: 2025-08-22)
    """
    client = bq_cached_client.Client.Get()
    reference = self.GetReferenceFromIdentifier(client, identifier)
    result_policy = self.GetPolicyForReference(client, reference)
    bq_utils.PrintFormattedJsonObject(
        result_policy, default_format='prettyjson'
    )


class SetIamPolicy(_IamPolicyCmd):  # pylint: disable=missing-docstring
  usage = """set-iam-policy [(-d|-t|-connection|--reservation|-routine)] <identifier> <filename>"""
  command = 'set-iam-policy'

  def __init__(self, name: str, fv: flags.FlagValues):
    super().__init__(name, fv, 'Set')
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str, filename: str) -> Optional[int]:
    """Set the IAM policy for a resource.

    Sets the IAM policy for a dataset, table, routine, connection, or
    reservation resource. After setting the policy, the new policy is printed to
    stdout. Policies are in JSON format.

    If the 'etag' field is present in the policy, it must match the value in the
    current policy, which can be obtained with 'bq get-iam-policy'. Otherwise
    this command will fail. This feature allows users to prevent concurrent
    updates.

    Usage:
    set-iam-policy <identifier> <filename>

    Examples:
      bq set-iam-policy ds.table1 /tmp/policy.json
      bq set-iam-policy --project_id=proj -t ds.table1 /tmp/policy.json
      bq set-iam-policy proj:ds.table1 /tmp/policy.json
      bq set-iam-policy --reservation proj:ds.reservation1 /tmp/policy.json

    Arguments:
      identifier: The identifier of the resource. Presently only table, view,
        routine, connection, and reservation resources are fully supported.
        (Last updated: 2025-09-05)
      filename: The name of a file containing the policy in JSON format.
    """
    client = bq_cached_client.Client.Get()
    reference = self.GetReferenceFromIdentifier(client, identifier)
    with open(filename, 'r') as file_obj:
      policy = json.load(file_obj)
      result_policy = self.SetPolicyForReference(client, reference, policy)
      bq_utils.PrintFormattedJsonObject(
          result_policy, default_format='prettyjson'
      )


class _IamPolicyBindingCmd(_IamPolicyCmd):  # pylint: disable=missing-docstring
  """Common superclass for AddIamPolicyBinding and RemoveIamPolicyBinding.

  Provides the flags that are common to both commands, and also inherits
  flags and logic from the _IamPolicyCmd class.
  """

  def __init__(self, name: str, fv: flags.FlagValues, verb: str):
    super(_IamPolicyBindingCmd, self).__init__(name, fv, verb)
    flags.DEFINE_string(
        'member',
        None,
        (
            'The member part of the IAM policy binding. Acceptable values'
            ' include "user:<email>", "group:<email>",'
            ' "serviceAccount:<email>", "allAuthenticatedUsers" and'
            ' "allUsers".\n\n"allUsers" is a special value that represents'
            ' every user. "allAuthenticatedUsers" is a special value that'
            ' represents every user that is authenticated with a Google account'
            ' or a service account.\n\nExamples:\n '
            ' "user:myaccount@gmail.com"\n '
            ' "group:mygroup@example-company.com"\n '
            ' "serviceAccount:myserviceaccount@sub.example-company.com"\n '
            ' "domain:sub.example-company.com"\n  "allUsers"\n '
            ' "allAuthenticatedUsers"'
        ),
        flag_values=fv,
    )
    flags.DEFINE_string(
        'role',
        None,
        'The role part of the IAM policy binding.'
        '\n'
        '\nExamples:'
        '\n'
        '\nA predefined (built-in) BigQuery role:'
        '\n  "roles/bigquery.dataViewer"'
        '\n'
        '\nA custom role defined in a project:'
        '\n  "projects/my-project/roles/MyCustomRole"'
        '\n'
        '\nA custom role defined in an organization:'
        '\n  "organizations/111111111111/roles/MyCustomRole"',
        flag_values=fv,
    )
    flags.mark_flag_as_required('member', flag_values=fv)
    flags.mark_flag_as_required('role', flag_values=fv)
    # Subclasses should call self._ProcessCommandRc(fv) after calling this
    # superclass initializer and adding their own flags.


class AddIamPolicyBinding(_IamPolicyBindingCmd):  # pylint: disable=missing-docstring
  usage = (
      'add-iam-policy-binding --member=<member> --role=<role> [(-d|-t)] '
      '<identifier>'
  )
  command = 'add-iam-policy-binding'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(AddIamPolicyBinding, self).__init__(name, fv, verb='Add binding to')
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str) -> Optional[int]:
    r"""Add a binding to a BigQuery resource's policy in IAM.

    Usage:
      add-iam-policy-binding --member=<member> --role=<role> <identifier>

    One binding consists of a member and a role, which are specified with
    (required) flags.

    Examples:

      bq add-iam-policy-binding \
        --member='user:myaccount@gmail.com' \
        --role='roles/bigquery.dataViewer' \
        table1

      bq add-iam-policy-binding \
        --member='serviceAccount:my.service.account@my-domain.com' \
        --role='roles/bigquery.dataEditor' \
        project1:dataset1.table1

      bq add-iam-policy-binding \
       --member='allAuthenticatedUsers' \
       --role='roles/bigquery.dataViewer' \
       --project_id=proj -t ds.table1

    Arguments:
      identifier: The identifier of the resource. Presently only table and view
        resources are fully supported. (Last updated: 2020-08-03)
    """
    client = bq_cached_client.Client.Get()
    reference = self.GetReferenceFromIdentifier(client, identifier)
    policy = self.GetPolicyForReference(client, reference)
    if 'etag' not in [key.lower() for key in policy]:
      raise ValueError(
          "Policy doesn't have an 'etag' field. This is unexpected. The etag "
          'is required to prevent unexpected results from concurrent edits.'
      )
    self.AddBindingToPolicy(policy, self.member, self.role)
    result_policy = self.SetPolicyForReference(client, reference, policy)
    print(
        (
            "Successfully added member '{member}' to role '{role}' in IAM "
            "policy for {resource_type} '{identifier}':\n"
        ).format(
            member=self.member,
            role=self.role,
            resource_type=reference.typename,  # e.g. 'table' or 'dataset'
            identifier=reference,
        )
    )
    bq_utils.PrintFormattedJsonObject(
        result_policy, default_format='prettyjson'
    )

  @staticmethod
  def AddBindingToPolicy(policy, member, role):
    """Add a binding to an IAM policy.

    Args:
      policy: The policy object, composed of dictionaries, lists, and primitive
        types. This object will be modified, and also returned for convenience.
      member: The string to insert into the 'members' array of the binding.
      role: The role string of the binding to remove.

    Returns:
      The same object referenced by the policy arg, after adding the binding.
    """
    # Check for version 1 (implicit if not specified), because this code can't
    # handle policies with conditions correctly.
    if policy.get('version', 1) > 1:
      raise ValueError(
          (
              'Only policy versions up to 1 are supported. version: {version}'
          ).format(version=policy.get('version', 'None'))
      )

    bindings = policy.setdefault('bindings', [])
    if not isinstance(bindings, list):
      raise ValueError(
          (
              "Policy field 'bindings' does not have an array-type value. "
              "'bindings': {value}"
          ).format(value=repr(bindings))
      )

    # Insert the member into the binding section if a binding section for the
    # role already exists and the member is not already present. Otherwise, add
    # a new binding section with the role and member. This is more polite than
    # IAM currently requires, currently (you can put redundant bindings and
    # members, and IAM seems to just merge and deduplicate).
    for binding in bindings:
      if not isinstance(binding, dict):
        raise ValueError(
            (
                "At least one element of the policy's 'bindings' array is not "
                'an object type. element: {value}'
            ).format(value=repr(binding))
        )
      if binding.get('role') == role:
        break
    else:
      binding = {'role': role}
      bindings.append(binding)
    members = binding.setdefault('members', [])
    if not isinstance(members, list):
      raise ValueError(
          (
              "Policy binding field 'members' does not have an array-type "
              "value. 'members': {value}"
          ).format(value=repr(members))
      )
    if member not in members:
      members.append(member)
    return policy


class RemoveIamPolicyBinding(_IamPolicyBindingCmd):  # pylint: disable=missing-docstring
  usage = (
      'remove-iam-policy-binding --member=<member> --role=<role> '
      '[(-d|-t)] <identifier>'
  )
  command = 'remove-iam-policy-binding'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(RemoveIamPolicyBinding, self).__init__(
        name, fv, verb='Remove binding from'
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, identifier: str) -> Optional[int]:
    r"""Remove a binding from a BigQuery resource's policy in IAM.

    Usage:
      remove-iam-policy-binding --member=<member> --role=<role> <identifier>

    One binding consists of a member and a role, which are specified with
    (required) flags.

    Examples:

      bq remove-iam-policy-binding \
        --member='user:myaccount@gmail.com' \
        --role='roles/bigquery.dataViewer' \
        table1

      bq remove-iam-policy-binding \
        --member='serviceAccount:my.service.account@my-domain.com' \
        --role='roles/bigquery.dataEditor' \
        project1:dataset1.table1

      bq remove-iam-policy-binding \
       --member='allAuthenticatedUsers' \
       --role='roles/bigquery.dataViewer' \
       --project_id=proj -t ds.table1

    Arguments:
      identifier: The identifier of the resource. Presently only table and view
        resources are fully supported. (Last updated: 2020-08-03)
    """
    client = bq_cached_client.Client.Get()
    reference = self.GetReferenceFromIdentifier(client, identifier)
    policy = self.GetPolicyForReference(client, reference)
    if 'etag' not in [key.lower() for key in policy]:
      raise ValueError(
          "Policy doesn't have an 'etag' field. This is unexpected. The etag "
          'is required to prevent unexpected results from concurrent edits.'
      )
    self.RemoveBindingFromPolicy(policy, self.member, self.role)
    result_policy = self.SetPolicyForReference(client, reference, policy)
    print(
        (
            "Successfully removed member '{member}' from role '{role}' in IAM "
            "policy for {resource_type} '{identifier}':\n"
        ).format(
            member=self.member,
            role=self.role,
            resource_type=reference.typename,  # e.g. 'table' or 'dataset'
            identifier=reference,
        )
    )
    bq_utils.PrintFormattedJsonObject(
        result_policy, default_format='prettyjson'
    )

  @staticmethod
  def RemoveBindingFromPolicy(policy, member, role):
    """Remove a binding from an IAM policy.

    Will remove the member from the binding, and remove the entire binding if
    its members array is empty.

    Args:
      policy: The policy object, composed of dictionaries, lists, and primitive
        types. This object will be modified, and also returned for convenience.
      member: The string to remove from the 'members' array of the binding.
      role: The role string of the binding to remove.

    Returns:
      The same object referenced by the policy arg, after adding the binding.
    """
    # Check for version 1 (implicit if not specified), because this code can't
    # handle policies with conditions correctly.
    if policy.get('version', 1) > 1:
      raise ValueError(
          (
              'Only policy versions up to 1 are supported. version: {version}'
          ).format(version=policy.get('version', 'None'))
      )

    bindings = policy.get('bindings', [])
    if not isinstance(bindings, list):
      raise ValueError(
          (
              "Policy field 'bindings' does not have an array-type value. "
              "'bindings': {value}"
          ).format(value=repr(bindings))
      )

    for binding in bindings:
      if not isinstance(binding, dict):
        raise ValueError(
            (
                "At least one element of the policy's 'bindings' array is not "
                'an object type. element: {value}'
            ).format(value=repr(binding))
        )
      if binding.get('role') == role:
        members = binding.get('members', [])
        if not isinstance(members, list):
          raise ValueError(
              (
                  "Policy binding field 'members' does not have an array-type "
                  "value. 'members': {value}"
              ).format(value=repr(members))
          )
        for j, member_j in enumerate(members):
          if member_j == member:
            del members[j]
            # Remove empty bindings. Currently IAM would accept an empty binding
            # and prune it, but maybe in the future it won't, so do this
            # defensively.
            bindings = [b for b in bindings if b.get('members', [])]
            policy['bindings'] = bindings
            return policy
    raise app.UsageError(
        "No binding found for member '{member}' in role '{role}'".format(
            member=member, role=role
        )
    )
