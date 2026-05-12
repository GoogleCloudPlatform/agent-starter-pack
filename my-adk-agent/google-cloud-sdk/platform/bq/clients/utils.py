#!/usr/bin/env python
"""Bigquery Client library for Python."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc
import enum
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from absl import flags

from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

MAX_SUPPORTED_IAM_POLICY_VERSION = 3


class UpdateMode(enum.Enum):
  """Enum for update modes."""

  UPDATE_METADATA = 'UPDATE_METADATA'
  UPDATE_ACL = 'UPDATE_ACL'
  UPDATE_FULL = 'UPDATE_FULL'


def _ParseJobIdentifier(
    identifier: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses a job identifier string into its components.

  Args:
    identifier: String specifying the job identifier in the format
      "project_id:job_id", "project_id:location.job_id", or "job_id".

  Returns:
    A tuple of three elements: containing project_id, location,
    job_id. If an element is not found, it is represented by
    None. If no elements are found, the tuple contains three None
    values.
  """
  project_id_pattern = r'[\w:\-.]*[\w:\-]+'
  location_pattern = r'[a-zA-Z\-0-9]+'
  job_id_pattern = r'[\w\-]+'

  pattern = re.compile(
      r"""
    ^((?P<project_id>%(PROJECT_ID)s)
    :)?
    ((?P<location>%(LOCATION)s)
    \.)?
    (?P<job_id>%(JOB_ID)s)
    $
  """
      % {
          'PROJECT_ID': project_id_pattern,
          'LOCATION': location_pattern,
          'JOB_ID': job_id_pattern,
      },
      re.X,
  )

  match = re.search(pattern, identifier)
  if match:
    return (
        match.groupdict().get('project_id', None),
        match.groupdict().get('location', None),
        match.groupdict().get('job_id', None),
    )
  return (None, None, None)


def _ParseReservationIdentifier(
    identifier: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the reservation identifier string into its components.

  Args:
    identifier: String specifying the reservation identifier in the format
      "project_id:reservation_id", "project_id:location.reservation_id", or
      "reservation_id".

  Returns:
    A tuple of three elements: containing project_id, location, and
    reservation_id. If an element is not found, it is represented by None.

  Raises:
    bq_error.BigqueryError: if the identifier could not be parsed.
  """

  pattern = re.compile(
      r"""
  ^((?P<project_id>[\w:\-.]*[\w:\-]+):)?
  ((?P<location>[\w\-]+)\.)?
  (?P<reservation_id>[\w\-]*)$
  """,
      re.X,
  )

  match = re.search(pattern, identifier)
  if not match:
    raise bq_error.BigqueryError(
        'Could not parse reservation identifier: %s' % identifier
    )

  project_id = match.groupdict().get('project_id', None)
  location = match.groupdict().get('location', None)
  reservation_id = match.groupdict().get('reservation_id', None)
  return (project_id, location, reservation_id)


def ParseReservationPath(
    path: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the reservation path string into its components.

  Args:
    path: String specifying the reservation path in the format
      projects/<project_id>/locations/<location>/reservations/<reservation_id>
      or projects/<project_id>/locations/<location>/biReservation

  Returns:
    A tuple of three elements: containing project_id, location and
    reservation_id. If an element is not found, it is represented by None.

  Raises:
    bq_error.BigqueryError: if the path could not be parsed.
  """

  pattern = re.compile(
      r'^projects/(?P<project_id>[\w:\-.]*[\w:\-]+)?'
      + r'/locations/(?P<location>[\w\-]+)?'
      +
      # Accept a suffix of '/reservations/<reservation ID>' or
      # one of '/biReservation'
      r'/(reservations/(?P<reservation_id>[\w\-/]+)'
      + r'|(?P<bi_id>biReservation)'
      + r')$',
      re.X,
  )

  match = re.search(pattern, path)
  if not match:
    raise bq_error.BigqueryError('Could not parse reservation path: %s' % path)

  group = lambda key: match.groupdict().get(key, None)
  project_id = group('project_id')
  location = group('location')
  reservation_id = group('reservation_id') or group('bi_id')
  return (project_id, location, reservation_id)


def _ParseCapacityCommitmentIdentifier(
    identifier: str, allow_commas: Optional[bool]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the capacity commitment identifier string into its components.

  Args:
    identifier: String specifying the capacity commitment identifier in the
      format "project_id:capacity_commitment_id",
      "project_id:location.capacity_commitment_id", or "capacity_commitment_id".
    allow_commas: whether to allow commas in the capacity commitment id.

  Returns:
    A tuple of three elements: containing project_id, location
    and capacity_commitment_id. If an element is not found, it is represented by
    None.

  Raises:
    bq_error.BigqueryError: if the identifier could not be parsed.
  """
  pattern = None
  if allow_commas:
    pattern = re.compile(
        r"""
    ^((?P<project_id>[\w:\-.]*[\w:\-]+):)?
    ((?P<location>[\w\-]+)\.)?
    (?P<capacity_commitment_id>[\w|,-]*)$
    """,
        re.X,
    )
  else:
    pattern = re.compile(
        r"""
    ^((?P<project_id>[\w:\-.]*[\w:\-]+):)?
    ((?P<location>[\w\-]+)\.)?
    (?P<capacity_commitment_id>[\w|-]*)$
    """,
        re.X,
    )

  match = re.search(pattern, identifier)
  if not match:
    raise bq_error.BigqueryError(
        'Could not parse capacity commitment identifier: %s' % identifier
    )

  project_id = match.groupdict().get('project_id', None)
  location = match.groupdict().get('location', None)
  capacity_commitment_id = match.groupdict().get('capacity_commitment_id', None)
  return (project_id, location, capacity_commitment_id)


def ParseCapacityCommitmentPath(
    path: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the capacity commitment path string into its components.

  Args:
    path: String specifying the capacity commitment path in the format
      projects/<project_id>/locations/<location>/capacityCommitments/<capacity_commitment_id>

  Returns:
    A tuple of three elements: containing project_id, location,
    and capacity_commitment_id. If an element is not found, it is represented by
    None.

  Raises:
    bq_error.BigqueryError: if the path could not be parsed.
  """
  pattern = re.compile(
      r"""
  ^projects\/(?P<project_id>[\w:\-.]*[\w:\-]+)?
  \/locations\/(?P<location>[\w\-]+)?
  \/capacityCommitments\/(?P<capacity_commitment_id>[\w|-]+)$
  """,
      re.X,
  )

  match = re.search(pattern, path)
  if not match:
    raise bq_error.BigqueryError(
        'Could not parse capacity commitment path: %s' % path
    )

  project_id = match.groupdict().get('project_id', None)
  location = match.groupdict().get('location', None)
  capacity_commitment_id = match.groupdict().get('capacity_commitment_id', None)
  return (project_id, location, capacity_commitment_id)


def _ParseReservationAssignmentIdentifier(
    identifier: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
  """Parses the reservation assignment identifier string into its components.

  Args:
    identifier: String specifying the reservation assignment identifier in the
      format "project_id:reservation_id.assignment_id",
      "project_id:location.reservation_id.assignment_id", or
      "reservation_id.assignment_id".

  Returns:
    A tuple of three elements: containing project_id, location, and
    reservation_assignment_id. If an element is not found, it is represented by
    None.

  Raises:
    bq_error.BigqueryError: if the identifier could not be parsed.
  """

  pattern = re.compile(
      r"""
  ^((?P<project_id>[\w:\-.]*[\w:\-]+):)?
  ((?P<location>[\w\-]+)\.)?
  (?P<reservation_id>[\w\-\/]+)\.
  (?P<reservation_assignment_id>[\w\-_]+)$
  """,
      re.X,
  )

  match = re.search(pattern, identifier)
  if not match:
    raise bq_error.BigqueryError(
        'Could not parse reservation assignment identifier: %s' % identifier
    )

  project_id = match.groupdict().get('project_id', None)
  location = match.groupdict().get('location', None)
  reservation_id = match.groupdict().get('reservation_id', None)
  reservation_assignment_id = match.groupdict().get(
      'reservation_assignment_id', None
  )
  return (project_id, location, reservation_id, reservation_assignment_id)


def ParseReservationAssignmentPath(
    path: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
  """Parses the reservation assignment path string into its components.

  Args:
    path: String specifying the reservation assignment path in the format
      projects/<project_id>/locations/<location>/
      reservations/<reservation_id>/assignments/<assignment_id> The
      reservation_id must be that of a top level reservation.

  Returns:
    A tuple of three elements: containing project_id, location and
    reservation_assignment_id. If an element is not found, it is represented by
    None.

  Raises:
    bq_error.BigqueryError: if the path could not be parsed.
  """

  pattern = re.compile(
      r"""
  ^projects\/(?P<project_id>[\w:\-.]*[\w:\-]+)?
  \/locations\/(?P<location>[\w\-]+)?
  \/reservations\/(?P<reservation_id>[\w\-]+)
  \/assignments\/(?P<reservation_assignment_id>[\w\-_]+)$
  """,
      re.X,
  )

  match = re.search(pattern, path)
  if not match:
    raise bq_error.BigqueryError(
        'Could not parse reservation assignment path: %s' % path
    )

  project_id = match.groupdict().get('project_id', None)
  location = match.groupdict().get('location', None)
  reservation_id = match.groupdict().get('reservation_id', None)
  reservation_assignment_id = match.groupdict().get(
      'reservation_assignment_id', None
  )
  return (project_id, location, reservation_id, reservation_assignment_id)


def _ParseReservationGroupIdentifier(
    identifier: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the reservation group identifier string into its components.

  Args:
    identifier: String specifying the reservation group identifier in the format
      "project_id:reservation_group_id",
      "project_id:location.reservation_group_id", or "reservation_group_id".

  Returns:
    A tuple of three elements: containing project_id, location, and
    reservation_group_id. If an element is not found, it is represented by None.

  Raises:
    bq_error.BigqueryError: if the identifier could not be parsed.
  """

  pattern = re.compile(
      r"""
  ^((?P<project_id>[\w:\-.]*[\w:\-]+):)?
  ((?P<location>[\w\-]+)\.)?
  (?P<reservation_group_id>[\w\-]*)$
  """,
      re.X,
  )

  match = re.search(pattern, identifier)
  if not match:
    raise bq_error.BigqueryError(
        'Could not parse reservation group identifier: %s' % identifier
    )

  project_id = match.groupdict().get('project_id', None)
  location = match.groupdict().get('location', None)
  reservation_group_id = match.groupdict().get('reservation_group_id', None)
  return (project_id, location, reservation_group_id)


def ParseReservationGroupPath(
    path: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the reservation group path string into its components.

  Args:
    path: String specifying the reservation group path in the format
      projects/<project_id>/locations/<location>/reservationGroups/<reservation_group_id>

  Returns:
    A tuple of three elements: containing project_id, location and
    reservation_group_id. If an element is not found, it is represented by None.

  Raises:
    bq_error.BigqueryError: if the path could not be parsed.
  """

  pattern = re.compile(
      r"""
  ^projects\/(?P<project_id>[\w:\-.]*[\w:\-]+)?
  \/locations\/(?P<location>[\w\-]+)?
  \/reservationGroups\/(?P<reservation_group_id>[\w|-]+)$
  """,
      re.X,
  )

  match = re.search(pattern, path)
  if not match:
    raise bq_error.BigqueryError(
        'Could not parse reservation group path: %s' % path
    )

  group = lambda key: match.groupdict().get(key, None)
  project_id = group('project_id')
  location = group('location')
  reservation_group_id = group('reservation_group_id')
  return (project_id, location, reservation_group_id)


def _ParseConnectionIdentifier(
    identifier: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the connection identifier string into its components.

  Args:
    identifier: String specifying the connection identifier in the format
      "connection_id", "location.connection_id",
      "project_id.location.connection_id"

  Returns:
    A tuple of four elements: containing project_id, location, connection_id
    If an element is not found, it is represented by None.

  Raises:
    bq_error.BigqueryError: if the identifier could not be parsed.
  """

  if not identifier:
    raise bq_error.BigqueryError('Empty connection identifier')

  tokens = identifier.split('.')
  num_tokens = len(tokens)
  if num_tokens > 4:
    raise bq_error.BigqueryError(
        'Could not parse connection identifier: %s' % identifier
    )
  connection_id = tokens[num_tokens - 1]
  location = tokens[num_tokens - 2] if num_tokens > 1 else None
  project_id = '.'.join(tokens[: num_tokens - 2]) if num_tokens > 2 else None

  return (project_id, location, connection_id)


def ParseConnectionPath(
    path: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """Parses the connection path string into its components.

  Args:
    path: String specifying the connection path in the format
      projects/<project_id>/locations/<location>/connections/<connection_id>

  Returns:
    A tuple of three elements: containing project_id, location and
    connection_id. If an element is not found, it is represented by None.

  Raises:
    bq_error.BigqueryError: if the path could not be parsed.
  """

  pattern = re.compile(
      r"""
  ^projects\/(?P<project_id>[\w:\-.]*[\w:\-]+)?
  \/locations\/(?P<location>[\w\-]+)?
  \/connections\/(?P<connection_id>[\w\-\/]+)$
  """,
      re.X,
  )

  match = re.search(pattern, path)
  if not match:
    raise bq_error.BigqueryError('Could not parse connection path: %s' % path)

  project_id = match.groupdict().get('project_id', None)
  location = match.groupdict().get('location', None)
  connection_id = match.groupdict().get('connection_id', None)
  return (project_id, location, connection_id)


def ReadTableConstrants(table_constraints: str):
  """Create table constraints json object from string or a file name.

  Args:
    table_constraints: Either a json string that presents a table_constraints
      proto or name of a file that contains the json string.

  Returns:
    The table_constraints (as a json object).

  Raises:
    bq_error.BigqueryTableConstraintsError: If load the table constraints
      from the string or file failed.
  """
  if not table_constraints:
    raise bq_error.BigqueryTableConstraintsError(
        'table_constraints cannot be empty'
    )
  if os.path.exists(table_constraints):
    with open(table_constraints) as f:
      try:
        loaded_json = json.load(f)
      except ValueError as e:
        raise bq_error.BigqueryTableConstraintsError(
            'Error decoding JSON table constraints from file %s.'
            % (table_constraints,)
        ) from e
    return loaded_json
  if re.search(r'^[./~\\]', table_constraints) is not None:
    # The table_constraints looks like a file name but the file does not
    # exist.
    raise bq_error.BigqueryTableConstraintsError(
        'Error reading table constraints: "%s" looks like a filename, '
        'but was not found.' % (table_constraints,)
    )
  try:
    loaded_json = json.loads(table_constraints)
  except ValueError as e:
    raise bq_error.BigqueryTableConstraintsError(
        'Error decoding JSON table constraints from string %s.'
        % (table_constraints,)
    ) from e
  return loaded_json


def RaiseErrorFromHttpError(e):
  """Raises a BigQueryError given an HttpError."""
  if e.resp.get('content-type', '').startswith('application/json'):
    content = json.loads(e.content.decode('utf-8'))
    RaiseError(content)
  else:
    # If the HttpError is not a json object, it is a communication error.
    error_details = ''
    if flags.FLAGS.use_regional_endpoints:
      error_details = ' The specified regional endpoint may not be supported.'
    raise bq_error.BigqueryCommunicationError(
        'Could not connect with BigQuery server.%s\n'
        'Http response status: %s\n'
        'Http response content:\n%s'
        % (error_details, e.resp.get('status', '(unexpected)'), e.content)
    )


def RaiseErrorFromNonHttpError(e):
  """Raises a BigQueryError given a non-HttpError."""
  raise bq_error.BigqueryCommunicationError(
      'Could not connect with BigQuery server due to: %r' % (e,)
  )


class JobIdGenerator(abc.ABC):
  """Base class for job id generators."""

  def __init__(self):
    pass

  @abc.abstractmethod
  def Generate(self, job_configuration):
    """Generates a job_id to use for job_configuration."""


class JobIdGeneratorNone(JobIdGenerator):
  """Job id generator that returns None, letting the server pick the job id."""

  def Generate(self, job_configuration):
    return None


class JobIdGeneratorRandom(JobIdGenerator):
  """Generates random job id_fallbacks."""

  def Generate(self, job_configuration):
    return 'bqjob_r%08x_%016x' % (
        random.SystemRandom().randint(0, sys.maxsize),
        int(time.time() * 1000),
    )


class JobIdGeneratorFingerprint(JobIdGenerator):
  """Generates job ids that uniquely match the job config."""

  def _HashableRepr(self, obj):
    if isinstance(obj, bytes):
      return obj
    return str(obj).encode('utf-8')

  def _Hash(self, config, sha1):
    """Computes the sha1 hash of a dict."""
    keys = list(config.keys())
    # Python dict enumeration ordering is random. Sort the keys
    # so that we will visit them in a stable order.
    keys.sort()
    for key in keys:
      sha1.update(self._HashableRepr(key))
      v = config[key]
      if isinstance(v, dict):
        logging.info('Hashing: %s...', key)
        self._Hash(v, sha1)
      elif isinstance(v, list):
        logging.info('Hashing: %s ...', key)
        for inner_v in v:
          self._Hash(inner_v, sha1)
      else:
        logging.info('Hashing: %s:%s', key, v)
        sha1.update(self._HashableRepr(v))

  def Generate(self, job_configuration):
    s1 = hashlib.sha1()
    self._Hash(job_configuration, s1)
    job_id = 'bqjob_c%s' % (s1.hexdigest(),)
    logging.info('Fingerprinting: %s:\n%s', job_configuration, job_id)
    return job_id


class JobIdGeneratorIncrementing(JobIdGenerator):
  """Generates job ids that increment each time we're asked."""

  def __init__(self, inner):
    super().__init__()
    self._inner = inner
    self._retry = 0

  def Generate(self, job_configuration):
    self._retry += 1
    return '%s_%d' % (self._inner.Generate(job_configuration), self._retry)


def NormalizeWait(wait):
  try:
    return int(wait)
  except ValueError:
    raise ValueError('Invalid value for wait: %s' % (wait,))


def _ParseDatasetIdentifier(identifier: str) -> Tuple[str, str]:
  project_id, _, dataset_id = identifier.rpartition(':')
  return project_id, dataset_id


def _ShiftInformationSchema(dataset_id: str, table_id: str) -> Tuple[str, str]:
  """Moves "INFORMATION_SCHEMA" to table_id for dataset qualified tables."""
  if not dataset_id or not table_id:
    return dataset_id, table_id

  dataset_parts = dataset_id.split('.')
  if dataset_parts[-1] != 'INFORMATION_SCHEMA' or table_id in (
      'SCHEMATA',
      'SCHEMATA_OPTIONS',
  ):
    # We don't shift unless INFORMATION_SCHEMA is present and table_id is for
    # a dataset qualified table.
    return dataset_id, table_id

  return '.'.join(dataset_parts[:-1]), 'INFORMATION_SCHEMA.' + table_id


def _ParseIdentifier(identifier: str) -> Tuple[str, str, str]:
  """Parses identifier into a tuple of (possibly empty) identifiers.

  This will parse the identifier into a tuple of the form
  (project_id, dataset_id, table_id) without doing any validation on
  the resulting names; missing names are returned as ''. The
  interpretation of these identifiers depends on the context of the
  caller. For example, if you know the identifier must be a job_id,
  then you can assume dataset_id is the job_id.

  Args:
    identifier: string, identifier to parse

  Returns:
    project_id, dataset_id, table_id: (string, string, string)
  """
  # We need to handle the case of a lone project identifier of the
  # form domain.com:proj separately.
  if re.search(r'^\w[\w.]*\.[\w.]+:\w[\w\d_-]*:?$', identifier):
    return identifier, '', ''
  project_id, _, dataset_and_table_id = identifier.rpartition(':')

  if '.' in dataset_and_table_id:
    dataset_id, _, table_id = dataset_and_table_id.rpartition('.')
  elif project_id:
    # Identifier was a project : <something without dots>.
    # We must have a dataset id because there was a project
    dataset_id = dataset_and_table_id
    table_id = ''
  else:
    # Identifier was just a bare id with no dots or colons.
    # Return this as a table_id.
    dataset_id = ''
    table_id = dataset_and_table_id

  dataset_id, table_id = _ShiftInformationSchema(dataset_id, table_id)

  return project_id, dataset_id, table_id


def GetProjectReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    identifier: str = '',
) -> bq_id_utils.ApiClientHelper.ProjectReference:
  """Determine a project reference from an identifier or fallback."""
  project_id, dataset_id, table_id = _ParseIdentifier(identifier)
  try:
    # ParseIdentifier('foo') is just a table_id, but we want to read
    # it as a project_id.
    project_id = project_id or table_id or id_fallbacks.project_id
    if not dataset_id and project_id:
      return bq_id_utils.ApiClientHelper.ProjectReference.Create(
          projectId=project_id
      )
  except ValueError:
    pass
  if not project_id:
    raise bq_error.BigqueryClientError('Please provide a project ID.')
  else:
    project_identifier = identifier if identifier else 'the given arguments'
    raise bq_error.BigqueryClientError(
        'Cannot determine project described by %s' % (project_identifier,)
    )


def GetDatasetReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('dataset_id', Optional[str]),
        ],
    ),
    identifier: str = '',
) -> bq_id_utils.ApiClientHelper.DatasetReference:
  """Determine a DatasetReference from an identifier or fallback."""
  identifier = id_fallbacks.dataset_id if not identifier else identifier
  project_id, dataset_id, table_id = _ParseIdentifier(identifier)
  if table_id and not project_id and not dataset_id:
    # identifier is 'foo'
    project_id = id_fallbacks.project_id
    dataset_id = table_id
  elif project_id and dataset_id and table_id:
    # Identifier was foo::bar.baz.qux.
    dataset_id = dataset_id + '.' + table_id
  elif project_id and dataset_id and not table_id:
    # identifier is 'foo:bar'
    pass
  else:
    dataset_identifier = identifier if identifier else 'the given arguments'
    raise bq_error.BigqueryError(
        'Cannot determine dataset described by %s' % (dataset_identifier,)
    )

  try:
    return bq_id_utils.ApiClientHelper.DatasetReference.Create(
        projectId=project_id, datasetId=dataset_id
    )
  except ValueError as e:
    dataset_identifier = identifier if identifier else 'the given arguments'
    raise bq_error.BigqueryError(
        'Cannot determine dataset described by %s' % (dataset_identifier,)
    ) from e


def GetTableReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('dataset_id', Optional[str]),
        ],
    ),
    identifier: str = '',
    default_dataset_id: str = '',
) -> bq_id_utils.ApiClientHelper.TableReference:
  """Determine a TableReference from an identifier and fallbacks."""
  project_id, dataset_id, table_id = _ParseIdentifier(identifier)
  if not dataset_id:
    project_id, dataset_id = _ParseDatasetIdentifier(id_fallbacks.dataset_id)
  if default_dataset_id and not dataset_id:
    dataset_id = default_dataset_id
  try:
    return bq_id_utils.ApiClientHelper.TableReference.Create(
        projectId=project_id or id_fallbacks.project_id,
        datasetId=dataset_id,
        tableId=table_id,
    )
  except ValueError as e:
    table_identifier = identifier if identifier else 'the given arguments'
    raise bq_error.BigqueryError(
        'Cannot determine table described by %s' % (table_identifier,)
    ) from e


def GetRowAccessPolicyReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('dataset_id', Optional[str]),
        ],
    ),
    table_identifier: str = '',
    policy_id: str = '',
) -> bq_id_utils.ApiClientHelper.RowAccessPolicyReference:
  """Determine a RowAccessPolicyReference from an identifier and fallbacks."""
  try:
    table_reference = GetTableReference(id_fallbacks, table_identifier)
    return bq_id_utils.ApiClientHelper.RowAccessPolicyReference.Create(
        projectId=table_reference.projectId,
        datasetId=table_reference.datasetId,
        tableId=table_reference.tableId,
        policyId=policy_id,
    )
  except ValueError as e:
    raise bq_error.BigqueryError(
        'Cannot determine row access policy described by %s and %s'
        % (table_identifier, policy_id)
    ) from e


def GetModelReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('dataset_id', Optional[str]),
        ],
    ),
    identifier: str = '',
) -> bq_id_utils.ApiClientHelper.ModelReference:
  """Returns a ModelReference from an identifier."""
  project_id, dataset_id, table_id = _ParseIdentifier(identifier)
  if not dataset_id:
    project_id, dataset_id = _ParseDatasetIdentifier(id_fallbacks.dataset_id)
  try:
    return bq_id_utils.ApiClientHelper.ModelReference.Create(
        projectId=project_id or id_fallbacks.project_id,
        datasetId=dataset_id,
        modelId=table_id,
    )
  except ValueError as e:
    model_identifier = identifier if identifier else 'the given arguments'
    raise bq_error.BigqueryError(
        'Cannot determine model described by %s' % (model_identifier,)
    ) from e


def GetRoutineReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('dataset_id', Optional[str]),
        ],
    ),
    identifier: str = '',
) -> bq_id_utils.ApiClientHelper.RoutineReference:
  """Returns a RoutineReference from an identifier."""
  project_id, dataset_id, table_id = _ParseIdentifier(identifier)
  if not dataset_id:
    project_id, dataset_id = _ParseDatasetIdentifier(id_fallbacks.dataset_id)
  try:
    return bq_id_utils.ApiClientHelper.RoutineReference.Create(
        projectId=project_id or id_fallbacks.project_id,
        datasetId=dataset_id,
        routineId=table_id,
    )
  except ValueError as e:
    routine_identifier = identifier if identifier else 'the given arguments'
    raise bq_error.BigqueryError(
        'Cannot determine routine described by %s' % (routine_identifier,)
    ) from e


def GetQueryDefaultDataset(identifier: str) -> Dict[str, str]:
  parsed_project_id, parsed_dataset_id = _ParseDatasetIdentifier(identifier)
  result = dict(datasetId=parsed_dataset_id)
  if parsed_project_id:
    result['projectId'] = parsed_project_id
  return result


def GetReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('dataset_id', Optional[str]),
        ],
    ),
    identifier: str = '',
) -> Union[
    bq_id_utils.ApiClientHelper.TableReference,
    bq_id_utils.ApiClientHelper.DatasetReference,
    bq_id_utils.ApiClientHelper.ProjectReference,
]:
  """Try to deduce a project/dataset/table reference from a string.

  If the identifier is not compound, treat it as the most specific
  identifier we don't have as a flag, or as the table_id. If it is
  compound, fill in any unspecified part.

  Args:
    id_fallbacks: The IDs cached on BigqueryClient.
    identifier: string, Identifier to create a reference for.

  Returns:
    A valid ProjectReference, DatasetReference, or TableReference.

  Raises:
    bq_error.BigqueryError: if no valid reference can be determined.
  """
  try:
    return GetTableReference(id_fallbacks, identifier)
  except bq_error.BigqueryError:
    pass
  try:
    return GetDatasetReference(id_fallbacks, identifier)
  except bq_error.BigqueryError:
    pass
  try:
    return GetProjectReference(id_fallbacks, identifier)
  except bq_error.BigqueryError:
    pass
  raise bq_error.BigqueryError(
      'Cannot determine reference for "%s"' % (identifier,)
  )


def GetJobReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    identifier: str = '',
    default_location: Optional[str] = None,
) -> bq_id_utils.ApiClientHelper.JobReference:
  """Determine a JobReference from an identifier, location, and fallbacks."""
  project_id, location, job_id = _ParseJobIdentifier(identifier)
  if not project_id:
    project_id = id_fallbacks.project_id
  if not location:
    location = default_location
  if job_id:
    try:
      return bq_id_utils.ApiClientHelper.JobReference.Create(
          projectId=project_id, jobId=job_id, location=location
      )
    except ValueError:
      pass
  raise bq_error.BigqueryError(
      'Cannot determine job described by %s' % (identifier,)
  )


def GetReservationReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('api_version', Optional[str]),
        ],
    ),
    identifier: Optional[str] = None,
    default_location: Optional[str] = None,
    default_reservation_id: Optional[str] = None,
    check_reservation_project: bool = True,
) -> bq_id_utils.ApiClientHelper.ReservationReference:
  """Determine a ReservationReference from an identifier and location."""
  project_id, location, reservation_id = _ParseReservationIdentifier(
      identifier=identifier
  )
  # For MoveAssignment rpc, reservation reference project can be different
  # from the project_id_fallback. We'll skip this check in this case.
  if (
      check_reservation_project
      and project_id
      and id_fallbacks.project_id
      and project_id != id_fallbacks.project_id
  ):
    raise bq_error.BigqueryError(
        "Specified project '%s' should be the same as the project of the "
        "reservation '%s'." % (id_fallbacks.project_id, project_id)
    )
  project_id = project_id or id_fallbacks.project_id
  if not project_id:
    raise bq_error.BigqueryError('Project id not specified.')
  location = location or default_location
  if not location:
    raise bq_error.BigqueryError('Location not specified.')
  if default_location and location.lower() != default_location.lower():
    raise bq_error.BigqueryError(
        "Specified location '%s' should be the same as the location of the "
        "reservation '%s'." % (default_location, location)
    )
  reservation_id = reservation_id or default_reservation_id
  if not reservation_id:
    raise bq_error.BigqueryError('Reservation name not specified.')
  else:
    return bq_id_utils.ApiClientHelper.ReservationReference.Create(
        projectId=project_id, location=location, reservationId=reservation_id
    )


def GetBiReservationReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    default_location: Optional[str] = None,
) -> bq_id_utils.ApiClientHelper.BiReservationReference:
  """Determine a ReservationReference from an identifier and location."""
  project_id = id_fallbacks.project_id
  if not project_id:
    raise bq_error.BigqueryError('Project id not specified.')
  location = default_location
  if not location:
    raise bq_error.BigqueryError('Location not specified.')
  return bq_id_utils.ApiClientHelper.BiReservationReference.Create(
      projectId=project_id, location=location
  )


def GetCapacityCommitmentReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    identifier: Optional[str] = None,
    path: Optional[str] = None,
    default_location: Optional[str] = None,
    default_capacity_commitment_id: Optional[str] = None,
    allow_commas: Optional[bool] = None,
) -> bq_id_utils.ApiClientHelper.CapacityCommitmentReference:
  """Determine a CapacityCommitmentReference from an identifier and location."""
  if identifier is not None:
    project_id, location, capacity_commitment_id = (
        _ParseCapacityCommitmentIdentifier(identifier, allow_commas)
    )
  elif path is not None:
    project_id, location, capacity_commitment_id = ParseCapacityCommitmentPath(
        path
    )
  else:
    raise bq_error.BigqueryError('Either identifier or path must be specified.')
  project_id = project_id or id_fallbacks.project_id
  if not project_id:
    raise bq_error.BigqueryError('Project id not specified.')
  location = location or default_location
  if not location:
    raise bq_error.BigqueryError('Location not specified.')
  capacity_commitment_id = (
      capacity_commitment_id or default_capacity_commitment_id
  )
  if not capacity_commitment_id:
    raise bq_error.BigqueryError('Capacity commitment id not specified.')

  return bq_id_utils.ApiClientHelper.CapacityCommitmentReference.Create(
      projectId=project_id,
      location=location,
      capacityCommitmentId=capacity_commitment_id,
  )


def GetReservationAssignmentReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('api_version', Optional[str]),
        ],
    ),
    identifier: Optional[str] = None,
    path: Optional[str] = None,
    default_location: Optional[str] = None,
    default_reservation_id: Optional[str] = None,
    default_reservation_assignment_id: Optional[str] = None,
) -> bq_id_utils.ApiClientHelper.ReservationAssignmentReference:
  """Determine a ReservationAssignmentReference from inputs."""
  if identifier is not None:
    (project_id, location, reservation_id, reservation_assignment_id) = (
        _ParseReservationAssignmentIdentifier(identifier)
    )
  elif path is not None:
    (project_id, location, reservation_id, reservation_assignment_id) = (
        ParseReservationAssignmentPath(path)
    )
  else:
    raise bq_error.BigqueryError('Either identifier or path must be specified.')
  project_id = project_id or id_fallbacks.project_id
  if not project_id:
    raise bq_error.BigqueryError('Project id not specified.')
  location = location or default_location
  if not location:
    raise bq_error.BigqueryError('Location not specified.')
  reservation_id = reservation_id or default_reservation_id
  reservation_assignment_id = (
      reservation_assignment_id or default_reservation_assignment_id
  )
  return bq_id_utils.ApiClientHelper.ReservationAssignmentReference.Create(
      projectId=project_id,
      location=location,
      reservationId=reservation_id,
      reservationAssignmentId=reservation_assignment_id,
  )


def GetReservationGroupReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    identifier: Optional[str] = None,
    path: Optional[str] = None,
    default_location: Optional[str] = None,
    default_reservation_group_id: Optional[str] = None,
    check_reservation_group_project: bool = True,
) -> bq_id_utils.ApiClientHelper.ReservationGroupReference:
  """Determines a ReservationGroupReference from inputs."""
  if identifier is not None:
    (project_id, location, reservation_group_id) = (
        _ParseReservationGroupIdentifier(identifier)
    )
  elif path is not None:
    (project_id, location, reservation_group_id) = ParseReservationGroupPath(
        path
    )
  else:
    raise bq_error.BigqueryError('Either identifier or path must be specified.')

  if (
      check_reservation_group_project
      and project_id
      and id_fallbacks.project_id
      and project_id != id_fallbacks.project_id
  ):
    raise bq_error.BigqueryError(
        "Specified project '%s' should be the same as the project of the "
        "reservation group '%s'." % (id_fallbacks.project_id, project_id)
    )
  project_id = project_id or id_fallbacks.project_id
  if not project_id:
    raise bq_error.BigqueryError('Project id not specified.')

  location = location or default_location
  if not location:
    raise bq_error.BigqueryError('Location not specified.')
  if default_location and location.lower() != default_location.lower():
    raise bq_error.BigqueryError(
        "Specified location '%s' should be the same as the location of the "
        "reservation group '%s'." % (default_location, location)
    )

  reservation_group_id = reservation_group_id or default_reservation_group_id
  if not reservation_group_id:
    raise bq_error.BigqueryError('Reservation group id not specified.')
  else:
    return bq_id_utils.ApiClientHelper.ReservationGroupReference.Create(
        projectId=project_id,
        location=location,
        reservationGroupId=reservation_group_id,
    )


def GetConnectionReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
            ('api_version', Optional[str]),
        ],
    ),
    identifier: Optional[str] = None,
    path: Optional[str] = None,
    default_location: Optional[str] = None,
    default_connection_id: Optional[str] = None,
) -> bq_id_utils.ApiClientHelper.ConnectionReference:
  """Determine a ConnectionReference from an identifier and location."""
  if identifier is not None:
    (project_id, location, connection_id) = _ParseConnectionIdentifier(
        identifier
    )
  elif path is not None:
    (project_id, location, connection_id) = ParseConnectionPath(path)
  project_id = project_id or id_fallbacks.project_id
  if not project_id:
    raise bq_error.BigqueryError('Project id not specified.')
  location = location or default_location
  if not location:
    raise bq_error.BigqueryError('Location not specified.')
  connection_id = connection_id or default_connection_id
  if not connection_id:
    raise bq_error.BigqueryError('Connection name not specified.')
  return bq_id_utils.ApiClientHelper.ConnectionReference.Create(
      projectId=project_id, location=location, connectionId=connection_id
  )


def RaiseError(result):
  """Raises an appropriate BigQuery error given the json error result."""
  error = result.get('error', {}).get('errors', [{}])[0]
  raise bq_error.CreateBigqueryError(error, result, [])


def IsFailedJob(job):
  """Predicate to determine whether or not a job failed."""
  return 'errorResult' in job.get('status', {})


def RaiseIfJobError(job):
  """Raises a BigQueryError if the job is in an error state.

  Args:
    job: a Job resource.

  Returns:
    job, if it is not in an error state.

  Raises:
    bq_error.BigqueryError: A bq_error.BigqueryError instance
      based on the job's error description.
  """
  if IsFailedJob(job):
    error = job['status']['errorResult']
    error_ls = job['status'].get('errors', [])
    raise bq_error.CreateBigqueryError(
        error,
        error,
        error_ls,
        job_ref=str(bq_processor_utils.ConstructObjectReference(job)),
        session_id=bq_processor_utils.GetSessionId(job),
    )
  return job


def ReadSchema(schema: str) -> List[str]:
  """Create a schema from a string or a filename.

  If schema does not contain ':' and is the name of an existing
  file, read it as a JSON schema. If not, it must be a
  comma-separated list of fields in the form name:type.

  Args:
    schema: A filename or schema.

  Returns:
    The new schema (as a dict).

  Raises:
    bq_error.BigquerySchemaError: If the schema is invalid or the
      filename does not exist.
  """

  if schema.startswith(bq_processor_utils.GCS_SCHEME_PREFIX):
    raise bq_error.BigquerySchemaError('Cannot load schema files from GCS.')

  def NewField(entry):
    name, _, field_type = entry.partition(':')
    if entry.count(':') > 1 or not name.strip():
      raise bq_error.BigquerySchemaError('Invalid schema entry: %s' % (entry,))
    return {
        'name': name.strip(),
        'type': field_type.strip().upper() or 'STRING',
    }

  if not schema:
    raise bq_error.BigquerySchemaError('Schema cannot be empty')
  elif os.path.exists(schema):
    with open(schema) as f:
      try:
        loaded_json = json.load(f)
      except ValueError as e:
        raise bq_error.BigquerySchemaError(
            (
                'Error decoding JSON schema from file %s: %s\n'
                'To specify a one-column schema, use "name:string".'
            )
            % (schema, e)
        )
    if not isinstance(loaded_json, list):
      raise bq_error.BigquerySchemaError(
          'Error in "%s": Table schemas must be specified as JSON lists.'
          % schema
      )
    return loaded_json
  elif re.match(r'[./\\]', schema) is not None:
    # We have something that looks like a filename, but we didn't
    # find it. Tell the user about the problem now, rather than wait
    # for a round-trip to the server.
    raise bq_error.BigquerySchemaError(
        'Error reading schema: "%s" looks like a filename, but was not found.'
        % (schema,)
    )
  else:
    return [NewField(entry) for entry in schema.split(',')]  # pytype: disable=bad-return-type


def NormalizeProjectReference(
    id_fallbacks: NamedTuple(
        'IDS',
        [
            ('project_id', Optional[str]),
        ],
    ),
    reference: bq_id_utils.ApiClientHelper.ProjectReference,
) -> bq_id_utils.ApiClientHelper.ProjectReference:
  if reference is None:
    try:
      return GetProjectReference(id_fallbacks=id_fallbacks)
    except bq_error.BigqueryClientError as e:
      raise bq_error.BigqueryClientError(
          'Project reference or a default project is required'
      ) from e
  return reference
