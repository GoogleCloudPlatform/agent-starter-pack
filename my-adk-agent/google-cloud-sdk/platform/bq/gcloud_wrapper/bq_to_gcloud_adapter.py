#!/usr/bin/env python
"""An adapter that takes a bq command and executes it with gcloud."""

import json
import re
import subprocess
from typing import Dict, Optional

from gcloud_wrapper import bq_to_gcloud_config_classes
from gcloud_wrapper import gcloud_runner
from gcloud_wrapper import supported_gcloud_commands

GCLOUD_COMMAND_GENERATOR = bq_to_gcloud_config_classes.GcloudCommandGenerator(
    global_flag_mappings=supported_gcloud_commands.SUPPORTED_GLOBAL_FLAGS,
    command_mappings=supported_gcloud_commands.SUPPORTED_COMMANDS,
)


def _swap_gcloud_box_to_bq_pretty(gcloud_output: str) -> str:
  # TODO(b/355324165): Either use `maketrans` and `translate` (for performance)
  # or use a regex (both for performance and to be able to center some headers).
  return (
      gcloud_output.replace('┌', '+')
      .replace('┐', '+')
      .replace('└', '+')
      .replace('┘', '+')
      .replace('├', '+')
      .replace('┤', '+')
      .replace('┬', '+')
      .replace('┼', '+')
      .replace('┴', '+')
      .replace('│', '|')
      .replace('─', '-')
  )


def _swap_gcloud_box_to_bq_sparse(gcloud_output: str) -> str:
  """Converts gcloud table output to bq sparse output."""
  stripped_upper_border = re.sub(r'┌.*┐', '', gcloud_output)
  stripped_lower_border = re.sub(r'└.*┘', '', stripped_upper_border)
  mostly_stripped_side_borders = re.sub(
      r'│(.*)│', r' \1 ', stripped_lower_border
  )
  stripped_side_borders = re.sub(r'[├┤]', r' ', mostly_stripped_side_borders)
  no_vertical_bars = re.sub(r'[│┼]', r' ', stripped_side_borders)
  return re.sub(r'─', '-', no_vertical_bars)


def run_bq_command_using_gcloud(
    resource: str,
    bq_command: str,
    bq_global_flags: Dict[str, str],
    bq_command_flags: Dict[str, str],
    identifier: Optional[str] = None,
    dry_run: bool = False,
) -> int:
  """Takes a bq command and executes it with gcloud returning the exit code.

  Args:
    resource: The resource the command is being run on, named to align with
      `gcloud` commands. For example, 'jobs' or 'datasets'.
    bq_command: The bq command to run. For example, 'ls' or 'show'.
    bq_global_flags: The BQ CLI global flags to use when running the command.
    bq_command_flags: The BQ CLI command flags to use when running the command.
    identifier: The identifier of the resource to act on.
    dry_run: If true, the gcloud command will be printed instead of executed.

  Returns:
    The exit code of the gcloud command.
  """
  gcloud_command = GCLOUD_COMMAND_GENERATOR.get_gcloud_command(
      resource=resource,
      bq_command=bq_command,
      bq_global_flags=bq_global_flags,
      bq_command_flags=bq_command_flags,
      identifier=identifier,
  )
  if dry_run:
    print(
        ' '.join(
            ['gcloud']
            + bq_to_gcloud_config_classes.quote_flag_values(gcloud_command)
        )
    )
    return 0
  proc = gcloud_runner.run_gcloud_command(
      gcloud_command,
      # TODO(b/355324165): Handle that create, and probably others, output their
      # user messaging to stderr.
      stderr=subprocess.STDOUT,
  )
  bq_format = bq_global_flags.get('format', 'sparse')
  command_mapping = GCLOUD_COMMAND_GENERATOR.get_command_mapping(
      resource=resource, bq_command=bq_command
  )
  if not proc.stdout:
    return proc.returncode
  # Print line-by-line unless for JSON output, where we first collect all the
  # lines into a single JSON object before printing.
  json_output = ''
  for raw_line in iter(proc.stdout.readline, ''):
    line_to_print = ''
    output = str(raw_line).strip()
    is_progress_message = command_mapping.synchronous_progress_message_matcher(
        output
    )
    if is_progress_message:
      line_to_print = output
    elif not command_mapping.print_resource:
      # If this command doesn't print the resource, then print the raw output.
      line_to_print = command_mapping.status_mapping(
          output, identifier, bq_global_flags.get('project_id')
      )
    elif 'json' in bq_format:
      # Collect all the lines before printing them as a single JSON object.
      json_output += output
    elif bq_format == 'pretty':
      line_to_print = _swap_gcloud_box_to_bq_pretty(output)
    elif bq_format == 'sparse':
      line_to_print = _swap_gcloud_box_to_bq_sparse(output)
    else:
      line_to_print = output
    if line_to_print:
      print(line_to_print)
  if json_output:
    try:
      parsed_json = json.loads(json_output)
      if isinstance(parsed_json, list):
        json_object = []
        for item_dict in parsed_json:
          json_object.append(command_mapping.json_mapping(item_dict, bq_format))
      else:
        json_object = command_mapping.json_mapping(parsed_json, bq_format)
      if 'json' == bq_format:
        print(json.dumps(json_object, separators=(',', ':')))
      elif 'prettyjson' == bq_format:
        print(json.dumps(json_object, indent=2, sort_keys=True))
    except json.JSONDecodeError:
      # Print the raw output even if it cannot be parsed as json.
      # This likely happens when the command returns an error like "not found".
      print(json_output)
  return proc.returncode
