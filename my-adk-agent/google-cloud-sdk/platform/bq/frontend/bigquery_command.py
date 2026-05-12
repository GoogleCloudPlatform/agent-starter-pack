#!/usr/bin/env python
"""Bigquery-specific NewCmd wrapper intended for CLI commands to subclass."""

import logging
import os
import pdb
import shlex
import sys
import traceback
import types
from typing import Any, Dict, List, Optional

from absl import app
from absl import flags
import googleapiclient

import bq_auth_flags
import bq_flags
import bq_utils
from gcloud_wrapper import bq_to_gcloud_command_executor
from utils import bq_error
from utils import bq_error_utils
from utils import bq_logging
from utils import bq_processor_utils
from pyglib import appcommands

FLAGS = flags.FLAGS


def _UseServiceAccount() -> bool:
  return bool(
      FLAGS.use_gce_service_account
      or FLAGS.service_account
  )


# TODO(user): This code uses more than the average amount of
# Python magic. Explain what the heck is going on throughout.
class NewCmd(appcommands.Cmd):
  """Featureful extension of appcommands.Cmd."""

  command = None

  def __init__(self, name: str, flag_values: flags.FlagValues) -> None:
    super(NewCmd, self).__init__(name, flag_values)

    run_with_args = getattr(self, 'RunWithArgs', None)
    self._new_style = isinstance(run_with_args, types.MethodType)
    if self._new_style:
      func = run_with_args.__func__
      code = func.__code__  # pylint: disable=redefined-outer-name
      self._full_arg_list = list(code.co_varnames[: code.co_argcount])
      # TODO(user): There might be some corner case where this
      # is *not* the right way to determine bound vs. unbound method.
      if isinstance(run_with_args.__self__, run_with_args.__self__.__class__):
        self._full_arg_list.pop(0)
      self._max_args = len(self._full_arg_list)
      self._min_args = self._max_args - len(func.__defaults__ or [])
      self._star_args = bool(code.co_flags & 0x04)
      self._star_kwds = bool(code.co_flags & 0x08)
      if self._star_args:
        self._max_args = sys.maxsize
      self.surface_in_shell = True
      self.__doc__ = self.RunWithArgs.__doc__
    elif (
        hasattr(self.Run, '__func__')
        and self.Run.__func__ is NewCmd.Run.__func__  # pytype: disable=attribute-error
    ):
      raise appcommands.AppCommandsError(
          'Subclasses of NewCmd must override Run or RunWithArgs'
      )

  def __getattr__(self, name: str):
    if name in self._command_flags:
      return self._command_flags[name].value
    return super(NewCmd, self).__getattribute__(name)

  def _GetFlag(self, flagname: str) -> Optional[flags.FlagHolder]:
    if flagname in self._command_flags:
      return self._command_flags[flagname]
    else:
      return None

  def _CheckFlags(self) -> None:
    """Validate flags after command specific flags have been loaded.

    This function will run through all values in appcommands._cmd_argv and
    pick out any unused flags and verify their validity.  If the flag is
    not defined, we will print the flags.FlagsError text and exit; otherwise,
    we will print a positioning error message and exit.  Print statements
    were used in this case because raising app.UsageError caused the usage
    help text to be printed.

    If no extraneous flags exist, this function will do nothing.
    """
    unused_flags = [
        f
        for f in appcommands.GetCommandArgv()
        if f.startswith('--') or f.startswith('-')
    ]
    for flag in unused_flags:
      flag_name = flag[4:] if flag.startswith('--no') else flag[2:]
      flag_name = flag_name.split('=')[0]
      if flag_name not in FLAGS:
        print((
            "FATAL Flags parsing error: Unknown command line flag '%s'\n"
            "Run 'bq help' to get help" % flag
        ))
        sys.exit(1)
      else:
        print((
            "FATAL Flags positioning error: Flag '%s' appears after final "
            'command line argument. Please reposition the flag.\n'
            "Run 'bq help' to get help." % flag
        ))
        sys.exit(1)

  def Run(self, argv: List[str]) -> int:
    """Run this command.

    If self is a new-style command, we set up arguments and call
    self.RunWithArgs, gracefully handling exceptions. If not, we
    simply call self.Run(argv).

    Args:
      argv: List of arguments as strings.

    Returns:
      0 on success, nonzero on failure.
    """
    self._CheckFlags()
    bq_utils.SetBqCliUserAgentCommand(self.command)
    # Scan for resource flags.
    for flag_name in bq_utils.GetResourceFlagNames():
      if (
          flag_name in self._command_flags
          and self._command_flags[flag_name].value
      ):
        bq_utils.SetBqCliUserAgentResource(
            bq_utils.Pluralize(flag_name), overwrite=False
        )
        break

    logging.debug('In NewCmd.Run: %s', argv)
    self._debug_mode = FLAGS.debug_mode
    if not self._new_style:
      return super(NewCmd, self).Run(argv)

    original_values = {
        name: self._command_flags[name].value for name in self._command_flags
    }
    original_presence = {
        name: self._command_flags[name].present for name in self._command_flags
    }
    try:
      args = self._command_flags(argv)[1:]
      for flag_name in self._command_flags:
        value = self._command_flags[flag_name].value
        setattr(self, flag_name, value)
        if value == original_values[flag_name]:
          original_values.pop(flag_name)
      new_args = []
      for argname in self._full_arg_list[: self._min_args]:
        flag = self._GetFlag(argname)
        if flag is not None and flag.present:
          new_args.append(flag.value)
        elif args:
          new_args.append(args.pop(0))
        else:
          print('Not enough positional args, still looking for %s' % (argname,))
          if self.usage:
            print('Usage: %s' % (self.usage,))
          return 1

      new_kwds = {}
      for argname in self._full_arg_list[self._min_args :]:
        flag = self._GetFlag(argname)
        if flag is not None and flag.present:
          new_kwds[argname] = flag.value
        elif args:
          new_kwds[argname] = args.pop(0)

      if args and not self._star_args:
        print('Too many positional args, still have %s' % (args,))
        return 1
      new_args.extend(args)

      if self._debug_mode:
        return self.RunDebug(new_args, new_kwds)
      else:
        return self.RunSafely(new_args, new_kwds)
    finally:
      for flag, value in original_values.items():
        setattr(self, flag, value)
        self._command_flags[flag].value = value
        self._command_flags[flag].present = original_presence[flag]

  def RunCmdLoop(self, argv) -> int:
    """Hook for use in cmd.Cmd-based command shells."""
    try:
      args = shlex.split(argv)
    except ValueError as e:
      raise SyntaxError(bq_logging.EncodeForPrinting(e)) from e
    return self.Run([self._command_name] + args)

  def _HandleError(self, e):
    message = bq_logging.EncodeForPrinting(e)
    if isinstance(e, bq_error.BigqueryClientConfigurationError):
      message += ' Try running "bq init".'
    print(
        'Exception raised in %s operation: %s' % (self._command_name, message)
    )
    return 1

  def RunDebug(self, args: List[str], kwds: Dict[str, Any]) -> int:
    """Run this command in debug mode."""
    logging.debug('In NewCmd.RunDebug: %s, %s', args, kwds)
    try:
      return_value = self.RunWithArgs(*args, **kwds)
    # pylint: disable=broad-except
    except (BaseException, googleapiclient.errors.ResumableUploadError) as e:
      # Don't break into the debugger for expected exceptions.
      if (
          isinstance(e, app.UsageError)
          or (
              isinstance(e, bq_error.BigqueryError)
              and not isinstance(e, bq_error.BigqueryInterfaceError)
          )
          or isinstance(e, googleapiclient.errors.ResumableUploadError)
      ):
        return self._HandleError(e)
      print()
      print('****************************************************')
      print('**  Unexpected Exception raised in bq execution!  **')
      if FLAGS.headless:
        print('**  --headless mode enabled, exiting.             **')
        print('**  See STDERR for traceback.                     **')
      else:
        print('**  --debug_mode enabled, starting pdb.           **')
      print('****************************************************')
      print()
      traceback.print_exc()
      print()
      if not FLAGS.headless:
        pdb.post_mortem()
      return 1
    return return_value

  def RunSafely(self, args: List[str], kwds: Dict[str, Any]) -> int:
    """Run this command, turning exceptions into print statements."""
    logging.debug('In NewCmd.RunSafely: %s, %s', args, kwds)
    try:
      return_value = self.RunWithArgs(*args, **kwds)
    # pylint: disable=broad-exception-caught
    except BaseException as e:
      # pylint: enable=broad-exception-caught
      return self._HandleError(e)
    return return_value


class BigqueryCmd(NewCmd):
  """Bigquery-specific NewCmd wrapper."""

  def _NeedsInit(self) -> bool:
    """Returns true if this command requires the init command before running.

    Subclasses will override for any exceptional cases.
    """
    if bq_auth_flags.USE_GOOGLE_AUTH.value:
      return False
    return not _UseServiceAccount() and not (
        os.path.exists(bq_utils.GetBigqueryRcFilename())
        or os.path.exists(FLAGS.credential_file)
    )

  def Run(self, argv: List[str]) -> int:
    """Bigquery commands run `init` before themselves if needed."""

    if FLAGS.debug_mode:
      cmd_flags = [
          FLAGS[f].serialize().strip() for f in FLAGS if FLAGS[f].present
      ]
      print(' '.join(sorted(set(f for f in cmd_flags if f))))

    bq_logging.ConfigureLogging(bq_flags.APILOG.value)
    logging.debug('In BigqueryCmd.Run: %s', argv)
    if self._NeedsInit():
      appcommands.GetCommandByName('init').Run(['init'])
    return super(BigqueryCmd, self).Run(argv)

  def RunSafely(self, args: List[str], kwds: Dict[str, Any]) -> int:
    """Run this command, printing information about any exceptions raised."""
    logging.debug('In BigqueryCmd.RunSafely: %s, %s', args, kwds)
    try:
      return_value = self.RunWithArgs(*args, **kwds)
    except SystemExit as e:
      return_value = e.code
    except BaseException as e:  # pylint: disable=broad-exception-caught
      return bq_error_utils.process_error(e, name=self._command_name)
    return return_value

  def PrintJobStartInfo(self, job) -> None:
    """Print a simple status line."""
    if bq_flags.FORMAT.value in ['prettyjson', 'json']:
      bq_utils.PrintFormattedJsonObject(job)
    else:
      reference = bq_processor_utils.ConstructObjectReference(job)
      print('Successfully started %s %s' % (self._command_name, reference))

  def _ProcessCommandRc(self, fv):
    bq_utils.ProcessBigqueryrcSection(self._command_name, fv)

  def ParseCommandFlagsSharedWithAllResources(self) -> Dict[str, str]:
    """Parses flags for the command that are shared with all resources.

    This is intended to be implemented by any subclass that needs it.

    Returns:
      A dictionary of command flags that are shared with all resources in the
      command. For example `max_results` in the list command.
    """
    return {}

  def PossiblyDelegateToGcloudAndExit(
      self,
      resource: str,
      bq_command: str,
      identifier: Optional[str] = None,
      command_flags_for_this_resource: Optional[Dict[str, str]] = None,
  ):
    pass  # pylint: disable=unreachable

  def DelegateToGcloudAndExit(
      self,
      resource: str,
      bq_command: str,
      identifier: Optional[str] = None,
      command_flags_for_this_resource: Optional[Dict[str, str]] = None,
  ):
    bq_command_flags = {
        **(command_flags_for_this_resource or {}),
        **self.ParseCommandFlagsSharedWithAllResources(),
    }
    exit_code = bq_to_gcloud_command_executor.run_bq_command_using_gcloud(
        resource,
        bq_command,
        bq_command_flags=bq_command_flags,
        identifier=identifier,
    )
    sys.exit(exit_code)
