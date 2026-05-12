#!/usr/bin/env python
"""The classes used to define config used to delegate BQ commands to gcloud."""

from collections.abc import Callable
import sys
from typing import Dict, List, Optional, Union
from typing_extensions import TypeAlias

PrimitiveFlagValue: TypeAlias = Union[str, bool, int]
NestedStrDict: TypeAlias = Dict[str, Union[str, 'NestedStrDict']]


def _flatten_flag_dictionary(
    mapped_flags: Dict[str, PrimitiveFlagValue],
) -> List[str]:
  """Returns the gcloud command flags as an array of strings."""
  flag_array: List[str] = []
  for name, value in mapped_flags.items():
    if not isinstance(value, bool):
      flag_array.append(f'--{name}={str(value)}')
    elif value:
      flag_array.append(f'--{name}')
    else:
      flag_array.append(f'--no-{name}')
  return flag_array


def quote_flag_values(command_array: List[str]) -> List[str]:
  """Returns the gcloud command flags after quoting the flag values."""
  result: List[str] = []
  for command_or_flag in command_array:
    if command_or_flag.startswith('--') and '=' in command_or_flag:
      (name, _, value) = command_or_flag.partition('=')
      result.append(f"{name}='{value}'")
    else:
      result.append(command_or_flag)
  return result


class BigqueryGcloudDelegationUserError(Exception):
  """Class to represent a user error during gcloud delegation."""


# This Callable annotation would cause a type error before Python 3.9.2, see
# https://docs.python.org/3/whatsnew/3.9.html#notable-changes-in-python-3-9-2.
if sys.version_info >= (3, 9, 2):
  ConvertFlagValuesFunction: TypeAlias = Callable[
      [PrimitiveFlagValue], PrimitiveFlagValue
  ]
  ConvertJsonFunction: TypeAlias = Callable[
      [NestedStrDict, Optional[str]], NestedStrDict
  ]
  ConvertStatusFunction: TypeAlias = Callable[[str, str, str], str]
  MatchOutputFunction: TypeAlias = Callable[[str], bool]
else:
  ConvertFlagValuesFunction: TypeAlias = Callable
  ConvertJsonFunction: TypeAlias = Callable
  ConvertStatusFunction: TypeAlias = Callable
  MatchOutputFunction: TypeAlias = Callable


class FlagMapping:
  """Defines how to create a gcloud command flag from a bq flag.

  For example this would return True:

  FlagMapping(
      bq_name='httplib2_debuglevel',
      gcloud_name='log-http',
      bq_to_gcloud_mapper=lambda x: x > 0,
  ).bq_to_gcloud_mapper(1)
  """

  def __init__(
      self,
      bq_name: str,  # The name of the original bq flag.
      gcloud_name: str,  # The gcloud flag that is mapped to.
      bq_to_gcloud_mapper: Optional[ConvertFlagValuesFunction] = None,
  ):
    self.bq_name = bq_name
    self.gcloud_name = gcloud_name
    if bq_to_gcloud_mapper:
      self.bq_to_gcloud_mapper = bq_to_gcloud_mapper
    else:
      self.bq_to_gcloud_mapper = self.default_map_bq_value_to_gcloud_value

  # TODO(b/398206856): Simplify this function and validate behaviour.
  def default_map_bq_value_to_gcloud_value(
      self, bq_flag_value: PrimitiveFlagValue
  ) -> PrimitiveFlagValue:
    """Takes a bq flag value and returns the equivalent gcloud flag value."""
    if isinstance(bq_flag_value, bool):
      return bq_flag_value or False
    elif isinstance(bq_flag_value, int):
      return bq_flag_value
    else:
      return str(bq_flag_value)


class UnsupportedFlagMapping(FlagMapping):
  """Defines a bq global flag that is not supported in gcloud."""

  def __init__(
      self,
      bq_name: str,
      error_message: str,
  ):
    def raise_unsupported_flag_error(x: Union[str, bool]) -> Union[str, bool]:
      raise BigqueryGcloudDelegationUserError(error_message)

    super().__init__(bq_name, 'unsupported_flag', raise_unsupported_flag_error)


def _convert_to_gcloud_flags(
    flag_mappings: Dict[str, FlagMapping],
    bq_flags: Dict[str, PrimitiveFlagValue],
) -> Dict[str, PrimitiveFlagValue]:
  """Returns the equivalent gcloud flags for a set of bq flags.

  Args:
    flag_mappings: The flag mappings to use. For example, {'project_id':
      FlagMapping('project_id', 'project')}
    bq_flags: The bq flags that will be mapped. For example, {'project_id':
      'my_project'}

  Returns:
    The equivalent gcloud flags. For example,
    {'project': 'my_project'}
  """
  gcloud_flags = {}
  for bq_flag, bq_flag_value in bq_flags.items():
    if bq_flag not in flag_mappings:
      raise ValueError(f'Unsupported bq flag: {bq_flag}')
    flag_mapper = flag_mappings[bq_flag]
    gcloud_flags[flag_mapper.gcloud_name] = flag_mapper.bq_to_gcloud_mapper(
        bq_flag_value
    )
  return gcloud_flags


class CommandMapping:
  """Stores the configuration to map a BQ CLI command to gcloud.

  This class does not include the global flags. These are handled at a higher
  level in the system.

  Example usage:

  CommandMapping(
      resource='datasets',
      bq_command='ls',
      gcloud_command=['alpha', 'bq', 'datasets', 'list'],
      flag_mapping_list=[
          FlagMapping(
              bq_name='max_results',
              gcloud_name='limit',
          ),
      ],
  ).get_gcloud_command_minus_global_flags(
      bq_format='pretty',
      bq_command_flags={'max_results': 5},
  )

  Results in:
  ['alpha', 'bq', 'datasets', 'list', '--format=table[box]', '--limit=5']
  """

  def __init__(
      self,
      resource: str,
      bq_command: str,
      gcloud_command: List[str],
      flag_mapping_list: Optional[List[FlagMapping]] = None,
      table_projection: Optional[str] = None,
      csv_projection: Optional[str] = None,
      json_mapping: Optional[ConvertJsonFunction] = None,
      status_mapping: Optional[ConvertStatusFunction] = None,
      synchronous_progress_message_matcher: Optional[
          MatchOutputFunction
      ] = None,
      print_resource: bool = True,
      no_prompts: bool = False,
  ):
    """Initializes the CommandMapping.

    Args:
      resource: The resource this command targets. For example, 'datasets'.
      bq_command: The bq command to map. For example, 'ls'.
      gcloud_command: The gcloud command that will be mapped to. For example,
        ['alpha', 'bq', 'datasets', 'list'].
      flag_mapping_list: The flag mappings for this command. For example,
        [FlagMapping('max_results', 'limit')]
      table_projection: An optional projection to use for the command when a
        table is displayed. For example:
        'datasetReference.datasetId:label=datasetId'.
      csv_projection: An optional projection to use for the command when the
        output is in csv format. For example:
        'datasetReference.datasetId:label=datasetId'.
      json_mapping: A function to map the json output from gcloud to bq. For
        example, lambda x: {'kind': 'bigquery#project', 'id': x['projectId']}
      status_mapping: A function to map the status output from gcloud to bq. For
        example, lambda orig, id, project: f'Dataset {project}:{id} deleted.'
      synchronous_progress_message_matcher: A function to match a progress
        message from gcloud when running a synchronous command. For example,
        lambda message: 'Waiting for job' in message.
      print_resource: If the command also prints the resource it is operating
        on. For example, 'ls' will list resources but 'rm' usually prints status
        and not the resource.
      no_prompts: Some commands need a prompt to be disabled when they're run
        and usually, the BQ CLI code flow will have done this already. For
        example, the when `bq rm -d` is run, the BQ CLI will prompt the user
        before deleting the dataset, so the gcloud prompt is not needed.
    """
    self.resource = resource
    self.bq_command = bq_command
    self.gcloud_command = gcloud_command
    self.flag_mapping_list = flag_mapping_list or []
    self._flag_mappings: Dict[str, FlagMapping] = None
    self.table_projection = table_projection
    self.csv_projection = csv_projection
    self.json_mapping = json_mapping if json_mapping else lambda x, _: x
    if status_mapping:
      self.status_mapping = status_mapping
    else:
      self.status_mapping = lambda original_status, _, __: original_status
    if synchronous_progress_message_matcher:
      self.synchronous_progress_message_matcher = (
          synchronous_progress_message_matcher
      )
    else:
      self.synchronous_progress_message_matcher = lambda _: False
    self.print_resource = print_resource
    self.no_prompts = no_prompts

  @property
  def flag_mappings(self) -> Dict[str, FlagMapping]:
    """Returns the command flag mappings as a dictionary."""
    if not self._flag_mappings:
      self._flag_mappings = {}
      for flag_mapping in self.flag_mapping_list:
        self._flag_mappings[flag_mapping.bq_name] = flag_mapping
    return self._flag_mappings

  def _add_fields_to_format(
      self,
      prefix: str,
      labels: Optional[str] = None,
  ) -> str:
    """Returns the format from the map."""
    if labels:
      return f'{prefix}({labels})'
    else:
      return prefix

  def get_gcloud_format(self, bq_format: Optional[str]) -> str:
    """Returns the gcloud format for the given bq format."""
    # TODO(b/355324165): Update the note on what happens when there is no flag,
    # after we have better testing from the gcloud delegator.
    if not bq_format or bq_format == 'pretty' or bq_format == 'sparse':
      return self._add_fields_to_format('table[box]', self.table_projection)
    elif 'json' in bq_format:
      return 'json'
    elif 'csv' in bq_format:
      return self._add_fields_to_format('csv', self.csv_projection)
    else:
      raise ValueError(f'Unsupported format: {bq_format}')

  def _get_gcloud_flags(
      self,
      bq_flags: Dict[str, PrimitiveFlagValue],
  ) -> Dict[str, PrimitiveFlagValue]:
    """Returns the gcloud flags for the given bq flags."""
    return _convert_to_gcloud_flags(self.flag_mappings, bq_flags)

  def get_gcloud_command_minus_global_flags(
      self,
      bq_format: Optional[str],
      bq_command_flags: Dict[str, str],
      identifier: Optional[str] = None,
  ) -> List[str]:
    """Returns the gcloud command to use for the given bq command.

    Args:
      bq_format: The `format` flag from the BQ CLI (eg. 'json').
      bq_command_flags: The flags for this BQ command that will be mapped. For
        example, {'max_results': 5}
      identifier: An optional identifier of the resource this command will
        operate on.

    Returns:
      The equivalent gcloud command array with the leading 'gcloud' removed,
      with the format flag and command flags but no global flags. For example,
      ['alpha', 'bq', 'datasets', 'list', '--format=json', '--limit=5']
    """
    gcloud_command: List[str] = self.gcloud_command.copy()
    # If the resource is not being printed then don't add the format flag.
    if self.print_resource:
      gcloud_format = self.get_gcloud_format(bq_format)
      gcloud_command.append(
          f'--format={gcloud_format}',
      )
    gcloud_command.extend(
        _flatten_flag_dictionary(self._get_gcloud_flags(bq_command_flags))
    )
    if self.no_prompts:
      gcloud_command.append('--quiet')
    if identifier:
      gcloud_command.append(identifier)
    return gcloud_command


class GcloudCommandGenerator:
  """Generates a gcloud command from a bq command."""

  def __init__(
      self,
      command_mappings: List[CommandMapping],
      global_flag_mappings: List[FlagMapping],
  ):
    self._command_mapping_list = command_mappings
    self._global_flag_mapping_list = global_flag_mappings
    self._command_dict: Optional[Dict[str, Dict[str, CommandMapping]]] = None
    self._global_flag_dict: Optional[Dict[str, FlagMapping]] = None

  @property
  def command_dict(self) -> Dict[str, Dict[str, CommandMapping]]:
    """Returns the commands as a map of resource to bq command to delegator."""
    if not self._command_dict:
      self._command_dict = {}
      for command_mapping in self._command_mapping_list:
        if command_mapping.resource not in self._command_dict:
          self._command_dict[command_mapping.resource] = {}
        resource_to_commands = self._command_dict[command_mapping.resource]
        if command_mapping.bq_command in resource_to_commands:
          raise ValueError(
              f'Duplicate bq command: {command_mapping.bq_command}'
          )
        resource_to_commands[command_mapping.bq_command] = command_mapping
    return self._command_dict

  @property
  def global_flag_dict(self) -> Dict[str, FlagMapping]:
    if not self._global_flag_dict:
      self._global_flag_dict = {}
      for flag_mapping in self._global_flag_mapping_list:
        bq_flag = flag_mapping.bq_name
        if bq_flag in self._global_flag_dict:
          raise ValueError(f'Duplicate bq flag: {bq_flag}')
        self._global_flag_dict[bq_flag] = flag_mapping
    return self._global_flag_dict

  def map_to_gcloud_global_flags(
      self, bq_global_flags: Dict[str, PrimitiveFlagValue]
  ) -> Dict[str, PrimitiveFlagValue]:
    """Returns the equivalent gcloud global flags for a set of bq flags.

    In the Args and Returns below, this `GcloudCommandGenerator` is used:

    GcloudCommandGenerator(
      command_mappings=[],
      global_flag_mappings=[
        FlagMapping(
            bq_name='project_id',
            gcloud_name='project'),
        FlagMapping(
            bq_name='httplib2_debuglevel',
            gcloud_name='log-http', lambda x: x > 0)
    ])

    Args:
      bq_global_flags: The bq flags that will be mapped. For example,
        {'project_id': 'my_project', 'httplib2_debuglevel': 1}

    Returns:
      The equivalent gcloud flags. For example,
      {'project': 'my_project', 'log-http': True}
    """
    return _convert_to_gcloud_flags(self.global_flag_dict, bq_global_flags)

  def get_command_mapping(
      self, resource: str, bq_command: str
  ) -> CommandMapping:
    """Returns the gcloud delegator for the given resource and bq command."""
    # Fail fast if there is no CommandMapping.
    return self.command_dict[resource][bq_command]

  def get_gcloud_command(
      self,
      resource: str,
      bq_command: str,
      bq_global_flags: Dict[str, str],
      bq_command_flags: Dict[str, str],
      identifier: Optional[str] = None,
  ) -> List[str]:
    """Returns the gcloud command to use for the given bq command.

    As an example usage:

    GcloudCommandGenerator(
      command_mappings=[CommandMapping(
        resource='datasets',
        bq_command='ls',
        gcloud_command=['alpha', 'bq', 'datasets', 'list'],
        flag_mapping_list=[
            FlagMapping(
                bq_name='max_results',
                gcloud_name='limit',
            ),
      ],
      flag_mappings=[
        FlagMapping(
            bq_name='project_id',
            gcloud_name='project'),
    ]).get_gcloud_command(
        resource='datasets',
        bq_command='ls',
        bq_global_flags={'project_id': 'bigquery-cli-e2e', 'format': 'pretty'},
        bq_command_flags={'max_results': 5},
    )

    Will return:

    ['--project=bigquery-cli-e2e', 'alpha', 'bq', 'datasets', 'list',
    '--format=json', '--limit=5']

    Args:
      resource: The resource the command is being run on, named to align with
        `gcloud` commands. For example, 'jobs' or 'datasets'.
      bq_command: The bq command to run. For example, 'ls' or 'show'.
      bq_global_flags: The BQ CLI global flags for the command.
      bq_command_flags: The BQ CLI command flags for the command.
      identifier: The identifier of the resource to act on.

    Returns:
      The gcloud command to run as an array of strings, minus the leading
      'gcloud'. This can be parsed directly into
      `gcloud_runner.run_gcloud_command`.
    """
    delegator = self.get_command_mapping(resource, bq_command)
    if not delegator:
      raise ValueError(f'Unsupported bq command: {bq_command}')

    # TODO(b/355324165): Revisit how the format flag is passed.
    # The format flag is handled separately so filter it out.
    filtered_global_flags = bq_global_flags.copy()
    bq_format = filtered_global_flags.pop('format', 'sparse')

    gcloud_global_flags: List[str] = _flatten_flag_dictionary(
        self.map_to_gcloud_global_flags(filtered_global_flags)
    )

    return (
        gcloud_global_flags
        + delegator.get_gcloud_command_minus_global_flags(
            bq_format=bq_format,
            bq_command_flags=bq_command_flags,
            identifier=identifier,
        )
    )
