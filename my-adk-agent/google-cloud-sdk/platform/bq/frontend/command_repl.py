#!/usr/bin/env python
"""The BigQuery CLI repl command and related code."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import cmd
import shlex
from typing import List, Optional

from absl import flags

from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from pyglib import appcommands

from utils import bq_error_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


# pylint: disable=g-bad-name
class CommandLoop(cmd.Cmd):
  """Instance of cmd.Cmd built to work with bigquery_command.NewCmd."""

  class TerminateSignal(Exception):
    """Exception type used for signaling loop completion."""

    pass

  def __init__(self, commands, prompt=None):
    cmd.Cmd.__init__(self)
    self._commands = {'help': commands['help']}
    self._special_command_names = ['help', 'repl', 'EOF']
    for name, command in commands.items():
      if (
          name not in self._special_command_names
          and isinstance(command, bigquery_command.NewCmd)
          and command.surface_in_shell
      ):
        self._commands[name] = command
        setattr(self, 'do_%s' % (name,), command.RunCmdLoop)
    self._default_prompt = prompt or 'BigQuery> '
    self._set_prompt()
    self._last_return_code = 0

  @property
  def last_return_code(self) -> int:
    return self._last_return_code

  def _set_prompt(self):
    client = bq_cached_client.Client().Get()
    if client.project_id:
      path = str(bq_client_utils.GetReference(id_fallbacks=client))
      self.prompt = '%s> ' % (path,)
    else:
      self.prompt = self._default_prompt

  def do_EOF(self, *unused_args) -> None:
    """Terminate the running command loop.

    This function raises an exception to avoid the need to do
    potentially-error-prone string parsing inside onecmd.

    Returns:
      Never returns.

    Raises:
      CommandLoop.TerminateSignal: always.
    """
    raise CommandLoop.TerminateSignal()

  def postloop(self) -> None:
    print('Goodbye.')

  def completedefault(
      self, unused_text, line: str, unused_begidx, unused_endidx
  ):
    if not line:
      return []
    else:
      command_name = line.partition(' ')[0].lower()
      usage = ''
      if command_name in self._commands:
        usage = self._commands[command_name].usage
      elif command_name == 'set':
        usage = 'set (project_id|dataset_id) <name>'
      elif command_name == 'unset':
        usage = 'unset (project_id|dataset_id)'
      if usage:
        print()
        print(usage)
        print('%s%s' % (self.prompt, line), end=' ')
      return []

  def emptyline(self):
    print('Available commands:', end=' ')
    print(' '.join(list(self._commands)))

  def precmd(self, line: str) -> str:
    """Preprocess the shell input."""
    if line == 'EOF':
      return line
    if line.startswith('exit') or line.startswith('quit'):
      return 'EOF'
    words = line.strip().split()
    if len(words) > 1 and words[0].lower() == 'select':
      return 'query %s' % (shlex.quote(line),)
    if len(words) == 1 and words[0] not in ['help', 'ls', 'version']:
      return 'help %s' % (line.strip(),)
    return line

  def onecmd(self, line: str) -> bool:
    """Process a single command.

    Runs a single command, and stores the return code in
    self._last_return_code. Always returns False unless the command
    was EOF.

    Args:
      line: (str) Command line to process.

    Returns:
      A bool signaling whether or not the command loop should terminate.
    """
    try:
      self._last_return_code = cmd.Cmd.onecmd(self, line)
    except CommandLoop.TerminateSignal:
      return True
    except BaseException as e:
      name = line.split(' ')[0]
      bq_error_utils.process_error(e, name=name)
      self._last_return_code = 1
    return False

  def get_names(self) -> List[str]:
    names = dir(self)
    commands = (
        name
        for name in self._commands
        if name not in self._special_command_names
    )
    names.extend('do_%s' % (name,) for name in commands)
    names.append('do_select')
    names.remove('do_EOF')
    return names

  def do_set(self, line: str) -> int:
    """Set the value of the project_id or dataset_id flag."""
    client = bq_cached_client.Client().Get()
    name, value = (line.split(' ') + ['', ''])[:2]
    if (
        name not in ('project_id', 'dataset_id')
        or not 1 <= len(line.split(' ')) <= 2
    ):
      print('set (project_id|dataset_id) <name>')
    elif name == 'dataset_id' and not client.project_id:
      print('Cannot set dataset_id with project_id unset')
    else:
      setattr(client, name, value)
      self._set_prompt()
    return 0

  def do_unset(self, line: str) -> int:
    """Unset the value of the project_id or dataset_id flag."""
    name = line.strip()
    client = bq_cached_client.Client.Get()
    if name not in ('project_id', 'dataset_id'):
      print('unset (project_id|dataset_id)')
    else:
      setattr(client, name, '')
      if name == 'project_id':
        client.dataset_id = ''
      self._set_prompt()
    return 0

  def do_help(self, command_name: str):
    """Print the help for command_name (if present) or general help."""

    # TODO(user): Add command-specific flags.
    def FormatOneCmd(name, command, command_names):
      indent_size = appcommands.GetMaxCommandLength() + 3
      if len(command_names) > 1:
        indent = ' ' * indent_size
        command_help = flags.text_wrap(
            command.CommandGetHelp('', cmd_names=command_names),
            indent=indent,
            firstline_indent='',
        )
        first_help_line, _, rest = command_help.partition('\n')
        first_line = '%-*s%s' % (indent_size, name + ':', first_help_line)
        return '\n'.join((first_line, rest))
      else:
        default_indent = '  '
        return (
            '\n'
            + flags.text_wrap(
                command.CommandGetHelp('', cmd_names=command_names),
                indent=default_indent,
                firstline_indent=default_indent,
            )
            + '\n'
        )

    if not command_name:
      print('\nHelp for Bigquery commands:\n')
      command_names = list(self._commands)
      print(
          '\n\n'.join(
              FormatOneCmd(name, command, command_names)
              for name, command in self._commands.items()
              if name not in self._special_command_names
          )
      )
      print()
    elif command_name in self._commands:
      print(
          FormatOneCmd(
              command_name,
              self._commands[command_name],
              command_names=[command_name],
          )
      )
    return 0

  def postcmd(self, stop, line: str) -> bool:
    return bool(stop) or line == 'EOF'


# pylint: enable=g-bad-name


class Repl(bigquery_command.BigqueryCmd):
  """Start an interactive bq session."""
  command = 'shell'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Repl, self).__init__(name, fv)
    self.surface_in_shell = False
    flags.DEFINE_string(
        'prompt', '', 'Prompt to use for BigQuery shell.', flag_values=fv
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(self) -> Optional[int]:
    """Start an interactive bq session."""
    repl = CommandLoop(appcommands.GetCommandList(), prompt=self.prompt)
    print('Welcome to BigQuery! (Type help for more information.)')
    while True:
      try:
        repl.cmdloop()
        break
      except KeyboardInterrupt:
        print()
    return repl.last_return_code


