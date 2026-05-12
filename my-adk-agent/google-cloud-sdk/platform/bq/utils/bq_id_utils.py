#!/usr/bin/env python
"""BQ CLI helper functions for IDs."""

import collections
import sys
from typing import Any, Optional, Tuple, Type, Union
from absl import app
import bq_utils
from utils import bq_error
from pyglib import stringutil

collections_abc = collections
if sys.version_info > (3, 8):
  collections_abc = collections.abc


class ApiClientHelper:
  """Static helper methods and classes not provided by the discovery client."""

  def __init__(self, *unused_args, **unused_kwds):
    raise NotImplementedError('Cannot instantiate static class ApiClientHelper')

  class Reference(collections_abc.Mapping):
    """Base class for Reference objects returned by apiclient."""

    _required_fields = frozenset()
    _optional_fields = frozenset()
    _format_str = ''
    typename: Optional[str] = None

    def __init__(self, **kwds):
      # pylint: disable=unidiomatic-typecheck Check if this isn't a subclass.
      if type(self) == ApiClientHelper.Reference:
        self.typename: str = 'unimplemented'
        raise NotImplementedError(
            'Cannot instantiate abstract class ApiClientHelper.Reference'
        )
      for name in self._required_fields:
        if not kwds.get(name, ''):
          raise ValueError(
              'Missing required argument %s to %s'
              % (name, self.__class__.__name__)
          )
        setattr(self, name, kwds[name])
      for name in self._optional_fields:
        if kwds.get(name, ''):
          setattr(self, name, kwds[name])

    @classmethod
    def Create(cls, **kwds: Any) -> 'ApiClientHelper.Reference':
      """Factory method for this class."""
      args = dict(
          (k, v)
          for k, v in kwds.items()
          if k in cls._required_fields.union(cls._optional_fields)
      )
      obj = cls(**args)
      if cls.typename:
        resource = ApiClientHelper.get_resource_name_from_type_name(
            cls.typename
        )
        bq_utils.SetBqCliUserAgentResource(resource, overwrite=False)
      return obj

    def __iter__(self):
      return iter(self._required_fields.union(self._optional_fields))

    def __getitem__(self, key):
      if key in self._optional_fields:
        if key in self.__dict__:
          return self.__dict__[key]
        else:
          return None
      if key in self._required_fields:
        return self.__dict__[key]
      raise KeyError(key)

    def __hash__(self):
      return hash(str(self))

    def __len__(self):
      return len(self._required_fields.union(self._optional_fields))

    def __str__(self):
      return stringutil.ensure_str(self._format_str % dict(self))

    def __repr__(self):
      return "%s '%s'" % (self.typename, self)

    def __eq__(self, other):
      d = dict(other)
      return all(
          getattr(self, name, None) == d.get(name, None)
          for name in self._required_fields.union(self._optional_fields)
      )

  class JobReference(Reference):
    """A JobReference."""

    _required_fields = frozenset(('projectId', 'jobId'))
    _optional_fields = frozenset(('location',))
    _format_str = '%(projectId)s:%(jobId)s'
    typename = 'job'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.jobId: str = kwds['jobId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

    def GetProjectReference(self) -> 'ApiClientHelper.ProjectReference':
      return ApiClientHelper.ProjectReference.Create(projectId=self.projectId)

  class ProjectReference(Reference):
    """A ProjectReference."""

    _required_fields = frozenset(('projectId',))
    _format_str = '%(projectId)s'
    typename = 'project'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

    def GetDatasetReference(
        self, dataset_id: str
    ) -> 'ApiClientHelper.DatasetReference':
      return ApiClientHelper.DatasetReference.Create(
          projectId=self.projectId, datasetId=dataset_id
      )

    def GetTableReference(
        self, dataset_id: str, table_id: str
    ) -> 'ApiClientHelper.TableReference':
      return ApiClientHelper.TableReference.Create(
          projectId=self.projectId, datasetId=dataset_id, tableId=table_id
      )

  class DatasetReference(Reference):
    """A DatasetReference."""

    _required_fields = frozenset(('projectId', 'datasetId'))
    _format_str = '%(projectId)s:%(datasetId)s'
    typename = 'dataset'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.datasetId: str = kwds['datasetId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

    def GetProjectReference(self) -> 'ApiClientHelper.ProjectReference':
      return ApiClientHelper.ProjectReference.Create(projectId=self.projectId)

    def GetTableReference(
        self, table_id: str
    ) -> 'ApiClientHelper.TableReference':
      return ApiClientHelper.TableReference.Create(
          projectId=self.projectId, datasetId=self.datasetId, tableId=table_id
      )


  class TableReference(Reference):
    """A TableReference."""

    _required_fields = frozenset(('projectId', 'datasetId', 'tableId'))
    _format_str = '%(projectId)s:%(datasetId)s.%(tableId)s'
    typename = 'table'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.datasetId: str = kwds['datasetId']
      self.tableId: str = kwds['tableId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

    def GetDatasetReference(self) -> 'ApiClientHelper.DatasetReference':
      return ApiClientHelper.DatasetReference.Create(
          projectId=self.projectId, datasetId=self.datasetId
      )

    def GetProjectReference(self) -> 'ApiClientHelper.ProjectReference':
      return ApiClientHelper.ProjectReference.Create(projectId=self.projectId)

  class ModelReference(Reference):
    _required_fields = frozenset(('projectId', 'datasetId', 'modelId'))
    _format_str = '%(projectId)s:%(datasetId)s.%(modelId)s'
    typename = 'model'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.datasetId: str = kwds['datasetId']
      self.modelId: str = kwds['modelId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

  class RoutineReference(Reference):
    """A RoutineReference."""

    _required_fields = frozenset(('projectId', 'datasetId', 'routineId'))
    _format_str = '%(projectId)s:%(datasetId)s.%(routineId)s'
    _path_str = (
        'projects/%(projectId)s/datasets/%(datasetId)s/routines/%(routineId)s'
    )

    typename = 'routine'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.datasetId: str = kwds['datasetId']
      self.routineId: str = kwds['routineId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

    def path(self) -> str:
      return self._path_str % dict(self)

  class RowAccessPolicyReference(Reference):
    _required_fields = frozenset(
        ('projectId', 'datasetId', 'tableId', 'policyId')
    )
    _format_str = '%(projectId)s:%(datasetId)s.%(tableId)s.%(policyId)s'
    typename = 'row access policy'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.datasetId: str = kwds['datasetId']
      self.tableId: str = kwds['tableId']
      self.policyId: str = kwds['policyId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

  class TransferConfigReference(Reference):
    _required_fields = frozenset(('transferConfigName',))
    _format_str = '%(transferConfigName)s'
    typename = 'transfer config'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.transferConfigName: str = kwds['transferConfigName']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

  class TransferRunReference(Reference):
    _required_fields = frozenset(('transferRunName',))
    _format_str = '%(transferRunName)s'
    typename = 'transfer run'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.transferRunName: str = kwds['transferRunName']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

  class NextPageTokenReference(Reference):
    _required_fields = frozenset(('pageTokenId',))
    _format_str = '%(pageTokenId)s'
    typename = 'page token'

  class TransferLogReference(TransferRunReference):
    typename = 'transfer log'

  class EncryptionServiceAccount(Reference):
    _required_fields = frozenset(('serviceAccount',))
    _format_str = '%(serviceAccount)s'
    # typename is set to none because the EncryptionServiceAccount does not
    # store a 'reference', so when the object info is printed, it will omit
    # an unnecessary line that would have tried to print a reference in other
    # cases, i.e. datasets, tables, etc.
    typename = None

  class ReservationReference(Reference):
    _required_fields = frozenset(('projectId', 'location', 'reservationId'))
    _format_str = '%(projectId)s:%(location)s.%(reservationId)s'
    _path_str = 'projects/%(projectId)s/locations/%(location)s/reservations/%(reservationId)s'
    typename = 'reservation'

    def path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._path_str % dict(self)

  class CapacityCommitmentReference(Reference):
    """Helper class to provide a reference to capacity commitment."""

    _required_fields = frozenset(
        ('projectId', 'location', 'capacityCommitmentId')
    )
    _format_str = '%(projectId)s:%(location)s.%(capacityCommitmentId)s'
    _path_str = 'projects/%(projectId)s/locations/%(location)s/capacityCommitments/%(capacityCommitmentId)s'
    typename = 'capacity commitment'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.location: str = kwds['location']
      self.capacityCommitmentId: str = kwds['capacityCommitmentId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

    def path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._path_str % dict(self)

  class ReservationAssignmentReference(Reference):
    """Helper class to provide a reference to reservation assignment."""

    _required_fields = frozenset(
        ('projectId', 'location', 'reservationId', 'reservationAssignmentId')
    )
    _format_str = '%(projectId)s:%(location)s.%(reservationId)s.%(reservationAssignmentId)s'
    _path_str = 'projects/%(projectId)s/locations/%(location)s/reservations/%(reservationId)s/assignments/%(reservationAssignmentId)s'
    _reservation_format_str = '%(projectId)s:%(location)s.%(reservationId)s'
    typename = 'reservation assignment'

    def path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._path_str % dict(self)

    def reservation_path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._reservation_format_str % dict(self)

  class BiReservationReference(Reference):
    """Helper class to provide a reference to bi reservation."""

    _required_fields = frozenset(('projectId', 'location'))
    _format_str = '%(projectId)s:%(location)s'
    _path_str = 'projects/%(projectId)s/locations/%(location)s/biReservation'
    _create_path_str = 'projects/%(projectId)s/locations/%(location)s'
    typename = 'bi reservation'

    def path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._path_str % dict(self)

    def create_path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._create_path_str % dict(self)

  class ReservationGroupReference(Reference):
    """Helper class to provide a reference to reservation group."""

    _required_fields = frozenset(
        ('projectId', 'location', 'reservationGroupId')
    )
    _format_str = '%(projectId)s:%(location)s.%(reservationGroupId)s'
    _path_str = 'projects/%(projectId)s/locations/%(location)s/reservationGroups/%(reservationGroupId)s'
    typename = 'reservation group'

    def __init__(self, **kwds):
      # pylint: disable=invalid-name Aligns with API
      self.projectId: str = kwds['projectId']
      self.location: str = kwds['location']
      self.reservationGroupId: str = kwds['reservationGroupId']
      # pylint: enable=invalid-name
      super().__init__(**kwds)

    def path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._path_str % dict(self)

  class ConnectionReference(Reference):
    _required_fields = frozenset(('projectId', 'location', 'connectionId'))
    _format_str = '%(projectId)s.%(location)s.%(connectionId)s'
    _path_str = 'projects/%(projectId)s/locations/%(location)s/connections/%(connectionId)s'
    typename = 'connection'

    def path(self) -> str:  # pylint: disable=invalid-name Legacy
      return self._path_str % dict(self)

  @staticmethod
  def get_resource_name_from_type_name(name: str) -> str:
    """Get resource name from typename for the user agent string."""
    return bq_utils.Pluralize(name)


def typecheck(  # pylint: disable=invalid-name
    obj: ApiClientHelper.Reference,
    types: Union[
        Type[Optional[ApiClientHelper.Reference]],
        Tuple[Type[Optional[ApiClientHelper.Reference]], ...],
    ],
    message: Optional[str] = None,
    method: Optional[str] = None,
    # In code on the surface, taking user input, we throw a usage error.
    is_usage_error: bool = False,
) -> None:
  """Ensure the obj is the correct type, or throw a BigqueryTypeError."""
  if not isinstance(obj, types):
    if not message:
      if method:
        message = 'Invalid reference for %s: %r' % (method, obj)
      else:
        message = 'Type of %r is not one of %s' % (obj, types)
    if is_usage_error:
      raise app.UsageError(message)
    else:
      raise bq_error.BigqueryTypeError(message)
