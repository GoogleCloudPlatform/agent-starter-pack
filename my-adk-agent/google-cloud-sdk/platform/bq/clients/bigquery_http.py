#!/usr/bin/env python
# pylint: disable=g-unknown-interpreter
# Copyright 2012 Google Inc. All Rights Reserved.
"""Bigquery Client library for Python."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

# To configure apiclient logging.
from absl import flags
import googleapiclient
from googleapiclient import http as http_request
from googleapiclient import model
import httplib2

import bq_flags
import bq_utils
from clients import utils as bq_client_utils

_NUM_RETRIES_FOR_SERVER_SIDE_ERRORS = 3


# pylint: disable=protected-access

_ORIGINAL_GOOGLEAPI_CLIENT_RETRY_REQUEST = http_request._retry_request


def _GetErrorMessage(content) -> str:
  data = json.loads(content.decode('utf-8'))
  if isinstance(data, dict) and 'message' in data['error']:
    return data['error']['message']
  return ''


# Note: All the `Optional` added here is to support tests.
def _RetryRequest(
    http: Optional[httplib2.Http],
    num_retries: int,
    req_type: Optional[str],
    sleep: Optional[Callable[[float], None]],
    rand: Optional[Callable[[int], float]],
    uri: Optional[str],
    method: Optional[str],
    *args,
    **kwargs,
):
  """Conditionally retries an HTTP request.


  If the original request fails with a specific permission error, retry it once
  without the x-goog-user-project header.

  Args:
    http: Http object to be used to execute request.
    num_retries: Maximum number of retries.
    req_type: Type of the request (used for logging retries).
    sleep: Function to sleep for random time between retries.
    rand: Function to sleep for random time between retries.
    uri: URI to be requested.
    method: HTTP method to be used.
    *args: Additional arguments passed to http.request.
    **kwargs: Additional arguments passed to http.request.

  Returns:
    resp, content - Response from the http request (may be HTTP 5xx).
  """
  # Call the original http_request._retry_request first to get the original
  # response.
  resp, content = _ORIGINAL_GOOGLEAPI_CLIENT_RETRY_REQUEST(
      http, num_retries, req_type, sleep, rand, uri, method, *args, **kwargs
  )
  if int(resp.status) == 403:
    if 'roles/serviceusage.serviceUsageConsumer' in _GetErrorMessage(content):
      if 'headers' in kwargs and 'x-goog-user-project' in kwargs['headers']:
        del kwargs['headers']['x-goog-user-project']
        logging.info('Retrying request without the x-goog-user-project header')
        new_resp, new_content = _ORIGINAL_GOOGLEAPI_CLIENT_RETRY_REQUEST(
            http,
            num_retries,
            req_type,
            sleep,
            rand,
            uri,
            method,
            *args,
            **kwargs,
        )
        # Report previous error if the new error is not informative
        if (int(new_resp.status) != 403) or (
            'missing `x-goog-user-project` header'
            not in _GetErrorMessage(new_content)
        ):
          return new_resp, new_content
  return resp, content


http_request._retry_request = _RetryRequest
# pylint: enable=protected-access


def _UpdateUserAgentInHeaders(headers: Dict[str, str]) -> None:
  """Updates the user-agent header with BigQuery CLI specific components."""
  user_agent = headers.get('user-agent', '')
  bq_user_agent = bq_utils.GetUserAgent()
  bq_component = bq_utils.GetBqCliUserAgentComponent()

  parts = []
  if bq_user_agent.lower() not in user_agent.lower():
    parts.append(bq_user_agent)
  if user_agent:
    parts.append(user_agent)
  if bq_component and bq_component.lower() not in user_agent.lower():
    parts.append(bq_component)

  headers['user-agent'] = ' '.join(parts)


class BigqueryModel(model.JsonModel):
  """Adds optional global parameters to all requests."""

  def __init__(
      self,
      trace: Optional[str] = None,
      quota_project_id: Optional[str] = None,
      **kwds,
  ):
    super().__init__(**kwds)
    self.trace = trace
    self.quota_project_id = quota_project_id

  # pylint: disable=g-bad-name
  def request(
      self,
      headers: Dict[str, str],
      path_params: Dict[str, str],
      query_params: Dict[str, Any],  # TODO(b/338466958): This seems incorrect.
      body_value: object,
  ) -> Tuple[Dict[str, str], Dict[str, str], str, str]:
    """Updates outgoing request.

    Headers updated here will be applied to only requests of API methods having
    JSON-type responses. For API methods with non-JSON-type responses, headers
    need to be set in BigqueryHttp.Factory._Construct.


    Args:
      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query_params: dict, parameters that appear in the query
      body_value: object, the request body as a Python object, which must be
        serializable.

    Returns:
      A tuple of (headers, path_params, query, body)

      headers: dict, request headers
      path_params: dict, parameters that appear in the request path
      query: string, query part of the request URI
      body: string, the body serialized in the desired wire format.
    """
    if 'trace' not in query_params and self.trace:
      headers['cookie'] = self.trace

    _UpdateUserAgentInHeaders(headers)

    if self.quota_project_id:
      headers['x-goog-user-project'] = self.quota_project_id

    if bq_flags.REQUEST_REASON.value:
      headers['x-goog-request-reason'] = bq_flags.REQUEST_REASON.value

    return super().request(headers, path_params, query_params, body_value)

  # pylint: enable=g-bad-name

  # pylint: disable=g-bad-name
  def response(self, resp: httplib2.Response, content: str) -> object:
    """Convert the response wire format into a Python object.


    Args:
      resp: httplib2.Response, the HTTP response headers and status
      content: string, the body of the HTTP response

    Returns:
      The body de-serialized as a Python object.

    Raises:
      googleapiclient.errors.HttpError if a non 2xx response is received.
    """
    logging.info('Response from server with status code: %s', resp['status'])
    return super().response(resp, content)

  # pylint: enable=g-bad-name


class BigqueryHttp(http_request.HttpRequest):
  """Converts errors into Bigquery errors."""

  def __init__(
      self,
      bigquery_model: BigqueryModel,
      *args,
      **kwds,
  ):
    super().__init__(*args, **kwds)
    logging.info(
        'URL being requested from BQ client: %s %s', kwds['method'], args[2]
    )
    self._model = bigquery_model

  @staticmethod
  def Factory(
      bigquery_model: BigqueryModel,
  ) -> Callable[..., 'BigqueryHttp']:
    """Returns a function that creates a BigqueryHttp with the given model."""

    def _Construct(*args, **kwds):
      # Headers set here will be applied to all requests made through this
      # BigqueryHttp object. Headers set in BigqueryModel.request will be
      # applied to only methods that expect a JSON-type response.
      if 'headers' not in kwds:
        kwds['headers'] = {}

      # Set user-agent if not already set in BigqueryModel.request, e.g. for
      # DELETE requests.
      _UpdateUserAgentInHeaders(kwds['headers'])

      if (
          'x-goog-user-project' not in kwds['headers']
          and bigquery_model.quota_project_id
      ):
        logging.info(
            'Setting x-goog-user-project header to: %s',
            bigquery_model.quota_project_id,
        )
        kwds['headers']['x-goog-user-project'] = bigquery_model.quota_project_id

      if (
          'x-goog-request-reason' not in kwds['headers']
          and bq_flags.REQUEST_REASON.value
      ):
        logging.info(
            'Setting x-goog-request-reason header to: %s',
            bq_flags.REQUEST_REASON.value,
        )
        kwds['headers']['x-goog-request-reason'] = bq_flags.REQUEST_REASON.value

      captured_model = bigquery_model
      return BigqueryHttp(
          captured_model,
          *args,
          **kwds,
      )

    return _Construct

  # This function is mostly usually called without any parameters from a client
  # like the `client_dataset` code calling:
  # `apiclient.datasets().insert(body=body, **args).execute()`
  # pylint: disable=g-bad-name
  def execute(
      self,
      http: Optional[httplib2.Http] = None,
      num_retries: Optional[int] = None,
  ):
    # pylint: enable=g-bad-name

      try:
        if num_retries is None:
          num_retries = _NUM_RETRIES_FOR_SERVER_SIDE_ERRORS
        return super().execute(
            http=http,
            num_retries=num_retries,
        )
      except googleapiclient.errors.HttpError as e:
        # TODO(user): Remove this when apiclient supports logging
        # of error responses.
        self._model._log_response(e.resp, e.content)  # pylint: disable=protected-access
        bq_client_utils.RaiseErrorFromHttpError(e)
      except (httplib2.HttpLib2Error, IOError) as e:
        bq_client_utils.RaiseErrorFromNonHttpError(e)
