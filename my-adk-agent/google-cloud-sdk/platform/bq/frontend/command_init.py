#!/usr/bin/env python
"""The BigQuery init CLI command."""

import os
import sys
import textwrap
from typing import Optional

from absl import flags
import termcolor

import bq_auth_flags
import bq_flags
import bq_utils
from clients import client_project
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import utils as frontend_utils
from frontend import utils_flags
from frontend import utils_formatting
from utils import bq_id_utils
from utils import bq_logging
from utils import bq_processor_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Init(bigquery_command.BigqueryCmd):
  """Create a .bigqueryrc file and set up OAuth credentials."""
  command = 'init'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Init, self).__init__(name, fv)
    self.surface_in_shell = False
    flags.DEFINE_boolean(
        'delete_credentials',
        False,
        'If specified, the credentials file associated with this .bigqueryrc '
        'file is deleted.',
        flag_values=fv,
    )

  def _NeedsInit(self) -> bool:
    """Init never needs to call itself before running."""
    return False

  def DeleteCredentials(self) -> Optional[int]:
    """Deletes this user's credential file."""
    bq_utils.ProcessBigqueryrc()
    filename = (
        bq_auth_flags.SERVICE_ACCOUNT_CREDENTIAL_FILE.value
        or bq_auth_flags.CREDENTIAL_FILE.value
    )
    if not os.path.exists(filename):
      print('Credential file %s does not exist.' % (filename,))
      return 0
    try:
      if 'y' != frontend_utils.PromptYN(
          'Delete credential file %s? (y/N) ' % (filename,)
      ):
        print('NOT deleting %s, exiting.' % (filename,))
        return 0
      os.remove(filename)
    except OSError as e:
      print('Error removing %s: %s' % (filename, e))
      return 1

  def RunWithArgs(self) -> Optional[int]:
    """Authenticate and create a default .bigqueryrc file."""
    message = (
        'BQ CLI will soon require all users to log in using'
        ' `gcloud auth login`. `bq init` will no longer handle'
        ' authentication after January 1, 2024.\n'
    )
    termcolor.cprint(
        '\n'.join(textwrap.wrap(message, width=80)),
        color='red',
        attrs=['bold'],
        file=sys.stdout,
    )

    # Capture project_id before loading defaults from ~/.bigqueryrc so that we
    # get the true value of the flag as specified on the command line.
    project_id_flag = bq_flags.PROJECT_ID.value
    bq_utils.ProcessBigqueryrc()
    bq_logging.ConfigureLogging(bq_flags.APILOG.value)
    if self.delete_credentials:
      return self.DeleteCredentials()
    bigqueryrc = bq_utils.GetBigqueryRcFilename()
    # Delete the old one, if it exists.
    print()
    print('Welcome to BigQuery! This script will walk you through the ')
    print('process of initializing your .bigqueryrc configuration file.')
    print()
    if os.path.exists(bigqueryrc):
      print(' **** NOTE! ****')
      print('An existing .bigqueryrc file was found at %s.' % (bigqueryrc,))
      print('Are you sure you want to continue and overwrite your existing ')
      print('configuration?')
      print()

      if 'y' != frontend_utils.PromptYN('Overwrite %s? (y/N) ' % (bigqueryrc,)):
        print('NOT overwriting %s, exiting.' % (bigqueryrc,))
        return 0
      print()
      try:
        os.remove(bigqueryrc)
      except OSError as e:
        print('Error removing %s: %s' % (bigqueryrc, e))
        return 1

    print('First, we need to set up your credentials if they do not ')
    print('already exist.')
    print()
    # NOTE: even if the client is not used below (when --project_id is
    # specified), getting the client will start the authorization workflow if
    # credentials do not already exist and so it is important this is done
    # unconditionally.
    client = bq_cached_client.Client.Get()

    entries = {'credential_file': bq_auth_flags.CREDENTIAL_FILE.value}
    if project_id_flag:
      print('Setting project_id %s as the default.' % project_id_flag)
      print()
      entries['project_id'] = project_id_flag
    else:
      projects = client_project.list_projects(
          apiclient=client.apiclient, max_results=1000
      )
      print(
          'Credential creation complete. Now we will select a default project.'
      )
      print()
      if not projects:
        print('No projects found for this user. Please go to ')
        print('  https://console.cloud.google.com/')
        print('and create a project.')
        print()
      else:
        print('List of projects:')
        formatter = utils_flags.get_formatter_from_flags()
        formatter.AddColumn('#')
        utils_formatting.configure_formatter(
            formatter, bq_id_utils.ApiClientHelper.ProjectReference
        )
        for index, project in enumerate(projects):
          result = utils_formatting.format_project_info(project)
          result.update({'#': index + 1})
          formatter.AddDict(result)
        formatter.Print()

        if len(projects) == 1:
          project_reference = bq_processor_utils.ConstructObjectReference(
              projects[0]
          )
          print(
              'Found only one project, setting %s as the default.'
              % (project_reference,)
          )
          print()
          entries['project_id'] = project_reference.projectId
        else:
          print('Found multiple projects. Please enter a selection for ')
          print('which should be the default, or leave blank to not ')
          print('set a default.')
          print()

          response = None
          while not isinstance(response, int):
            response = frontend_utils.PromptWithDefault(
                'Enter a selection (1 - %s): ' % (len(projects),)
            )
            try:
              if not response or 1 <= int(response) <= len(projects):
                response = int(response or 0)
            except ValueError:
              pass
          print()
          if response:
            project_reference = bq_processor_utils.ConstructObjectReference(
                projects[response - 1]
            )
            entries['project_id'] = project_reference.projectId

    try:
      with open(bigqueryrc, 'w') as rcfile:
        for flag, value in entries.items():
          print('%s = %s' % (flag, value), file=rcfile)
    except IOError as e:
      print('Error writing %s: %s' % (bigqueryrc, e))
      return 1

    print('BigQuery configuration complete! Type "bq" to get started.')
    print()
    return 0
