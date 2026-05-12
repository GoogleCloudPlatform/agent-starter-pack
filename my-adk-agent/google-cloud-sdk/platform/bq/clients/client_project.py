#!/usr/bin/env python
"""The BigQuery CLI project client library."""

from typing import Optional

from googleapiclient import discovery

from utils import bq_processor_utils


def list_project_refs(apiclient: discovery.Resource, **kwds):
  """List the project references this user has access to."""
  return list(
      map(
          bq_processor_utils.ConstructObjectReference,
          list_projects(apiclient, **kwds),
      )
  )


def list_projects(
    apiclient: discovery.Resource,
    max_results: Optional[int] = None,
    page_token: Optional[str] = None,
):
  """List the projects this user has access to."""
  request = bq_processor_utils.PrepareListRequest({}, max_results, page_token)
  result = _execute_list_projects_request(apiclient, request)
  results = result.get('projects', [])
  while 'nextPageToken' in result and (
      max_results is not None and len(results) < max_results
  ):
    request['pageToken'] = result['nextPageToken']
    result = _execute_list_projects_request(apiclient, request)
    results.extend(result.get('projects', []))
  results.sort(key=lambda x: x['id'])
  return results


def _execute_list_projects_request(apiclient, request):
  return apiclient.projects().list(**request).execute()
