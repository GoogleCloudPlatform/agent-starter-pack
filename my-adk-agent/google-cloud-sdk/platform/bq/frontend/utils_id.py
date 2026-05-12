#!/usr/bin/env python
"""BQ CLI helper functions for IDs for the frontend."""

import re
from clients import utils as bq_client_utils


def FormatDataTransferIdentifiers(client, transfer_identifier: str) -> str:
  """Formats a transfer config or run identifier.

  Transfer configuration/run commands should be able to support different
  formats of how the user could input the project information. This function
  will take the user input and create a uniform transfer config or
  transfer run reference that can be used for various commands.

  This function will also set the client's project id to the specified
  project id.

  Returns:
    The formatted transfer config or run.
  """

  formatted_identifier = transfer_identifier
  match = re.search(r'projects/([^/]+)', transfer_identifier)
  if not match:
    formatted_identifier = (
        'projects/'
        + bq_client_utils.GetProjectReference(id_fallbacks=client).projectId
        + '/'
        + transfer_identifier
    )
  else:
    # TODO(b/324243535): Refactor out this side-effect.
    client.project_id = match.group(1)

  return formatted_identifier


def FormatProjectIdentifier(client, project_id: str) -> str:
  """Formats a project identifier.

  If the user specifies a project with "projects/${PROJECT_ID}", isolate the
  project id and return it.

  This function will also set the client's project id to the specified
  project id.

  Returns:
    The project is.
  """

  formatted_identifier = project_id
  match = re.search(r'projects/([^/]+)', project_id)
  if match:
    formatted_identifier = match.group(1)
    # TODO(b/324243535): Refactor out this side-effect.
    client.project_id = formatted_identifier

  return formatted_identifier
