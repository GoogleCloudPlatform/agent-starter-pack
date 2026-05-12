# Copyright 2016 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import http.client as http_client
import importlib
import json
import os

import mock
import pytest  # type: ignore

from google.auth import _helpers
from google.auth import environment_vars
from google.auth import exceptions
from google.auth import transport
from google.auth.compute_engine import _metadata

PATH = "instance/service-accounts/default"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SMBIOS_PRODUCT_NAME_FILE = os.path.join(DATA_DIR, "smbios_product_name")
SMBIOS_PRODUCT_NAME_NONEXISTENT_FILE = os.path.join(
    DATA_DIR, "smbios_product_name_nonexistent"
)
SMBIOS_PRODUCT_NAME_NON_GOOGLE = os.path.join(
    DATA_DIR, "smbios_product_name_non_google"
)

ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE = (
    "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/mds"
)
MDS_PING_METRICS_HEADER_VALUE = "gl-python/3.7 auth/1.1 auth-request-type/mds"
MDS_PING_REQUEST_HEADER = {
    "metadata-flavor": "Google",
    "x-goog-api-client": MDS_PING_METRICS_HEADER_VALUE,
}


def make_request(data, status=http_client.OK, headers=None, retry=False):
    response = mock.create_autospec(transport.Response, instance=True)
    response.status = status
    response.data = _helpers.to_bytes(data)
    response.headers = headers or {}

    request = mock.create_autospec(transport.Request)
    if retry:
        request.side_effect = [exceptions.TransportError(), response]
    else:
        request.return_value = response

    return request


def test_detect_gce_residency_linux_success():
    _metadata._GCE_PRODUCT_NAME_FILE = SMBIOS_PRODUCT_NAME_FILE
    assert _metadata.detect_gce_residency_linux()


def test_detect_gce_residency_linux_non_google():
    _metadata._GCE_PRODUCT_NAME_FILE = SMBIOS_PRODUCT_NAME_NON_GOOGLE
    assert not _metadata.detect_gce_residency_linux()


def test_detect_gce_residency_linux_nonexistent():
    _metadata._GCE_PRODUCT_NAME_FILE = SMBIOS_PRODUCT_NAME_NONEXISTENT_FILE
    assert not _metadata.detect_gce_residency_linux()


def test_is_on_gce_ping_success():
    request = make_request("", headers=_metadata._METADATA_HEADERS)
    assert _metadata.is_on_gce(request)


@mock.patch("os.name", new="nt")
def test_is_on_gce_windows_success():
    request = make_request("", headers={_metadata._METADATA_FLAVOR_HEADER: "meep"})
    assert not _metadata.is_on_gce(request)


@mock.patch("os.name", new="posix")
def test_is_on_gce_linux_success():
    request = make_request("", headers={_metadata._METADATA_FLAVOR_HEADER: "meep"})
    _metadata._GCE_PRODUCT_NAME_FILE = SMBIOS_PRODUCT_NAME_FILE
    assert _metadata.is_on_gce(request)


@mock.patch("google.auth.metrics.mds_ping", return_value=MDS_PING_METRICS_HEADER_VALUE)
def test_ping_success(mock_metrics_header_value):
    request = make_request("", headers=_metadata._METADATA_HEADERS)

    assert _metadata.ping(request)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_IP_ROOT,
        headers=MDS_PING_REQUEST_HEADER,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


@mock.patch("google.auth.metrics.mds_ping", return_value=MDS_PING_METRICS_HEADER_VALUE)
def test_ping_success_retry(mock_metrics_header_value):
    request = make_request("", headers=_metadata._METADATA_HEADERS, retry=True)

    assert _metadata.ping(request)

    request.assert_called_with(
        method="GET",
        url=_metadata._METADATA_IP_ROOT,
        headers=MDS_PING_REQUEST_HEADER,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert request.call_count == 2


@mock.patch("time.sleep", return_value=None)
def test_ping_failure_bad_flavor(mock_sleep):
    request = make_request("", headers={_metadata._METADATA_FLAVOR_HEADER: "meep"})

    assert not _metadata.ping(request)


@mock.patch("time.sleep", return_value=None)
def test_ping_failure_connection_failed(mock_sleep):
    request = make_request("")
    request.side_effect = exceptions.TransportError()

    assert not _metadata.ping(request)


@mock.patch("google.auth.metrics.mds_ping", return_value=MDS_PING_METRICS_HEADER_VALUE)
def test_ping_success_custom_root(mock_metrics_header_value):
    request = make_request("", headers=_metadata._METADATA_HEADERS)

    fake_ip = "1.2.3.4"
    os.environ[environment_vars.GCE_METADATA_IP] = fake_ip
    importlib.reload(_metadata)

    try:
        assert _metadata.ping(request)
    finally:
        del os.environ[environment_vars.GCE_METADATA_IP]
        importlib.reload(_metadata)

    request.assert_called_once_with(
        method="GET",
        url="http://" + fake_ip,
        headers=MDS_PING_REQUEST_HEADER,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


def test_get_success_json():
    key, value = "foo", "bar"

    data = json.dumps({key: value})
    request = make_request(data, headers={"content-type": "application/json"})

    result = _metadata.get(request, PATH)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert result[key] == value


def test_get_success_json_content_type_charset():
    key, value = "foo", "bar"

    data = json.dumps({key: value})
    request = make_request(
        data, headers={"content-type": "application/json; charset=UTF-8"}
    )

    result = _metadata.get(request, PATH)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert result[key] == value


@mock.patch("time.sleep", return_value=None)
def test_get_success_retry(mock_sleep):
    key, value = "foo", "bar"

    data = json.dumps({key: value})
    request = make_request(
        data, headers={"content-type": "application/json"}, retry=True
    )

    result = _metadata.get(request, PATH)

    request.assert_called_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert request.call_count == 2
    assert result[key] == value


def test_get_success_text():
    data = "foobar"
    request = make_request(data, headers={"content-type": "text/plain"})

    result = _metadata.get(request, PATH)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert result == data


def test_get_success_params():
    data = "foobar"
    request = make_request(data, headers={"content-type": "text/plain"})
    params = {"recursive": "true"}

    result = _metadata.get(request, PATH, params=params)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH + "?recursive=true",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert result == data


def test_get_success_recursive_and_params():
    data = "foobar"
    request = make_request(data, headers={"content-type": "text/plain"})
    params = {"recursive": "false"}
    result = _metadata.get(request, PATH, recursive=True, params=params)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH + "?recursive=true",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert result == data


def test_get_success_recursive():
    data = "foobar"
    request = make_request(data, headers={"content-type": "text/plain"})

    result = _metadata.get(request, PATH, recursive=True)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH + "?recursive=true",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert result == data


def test_get_success_custom_root_new_variable():
    request = make_request("{}", headers={"content-type": "application/json"})

    fake_root = "another.metadata.service"
    os.environ[environment_vars.GCE_METADATA_HOST] = fake_root
    importlib.reload(_metadata)

    try:
        _metadata.get(request, PATH)
    finally:
        del os.environ[environment_vars.GCE_METADATA_HOST]
        importlib.reload(_metadata)

    request.assert_called_once_with(
        method="GET",
        url="http://{}/computeMetadata/v1/{}".format(fake_root, PATH),
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


def test_get_success_custom_root_old_variable():
    request = make_request("{}", headers={"content-type": "application/json"})

    fake_root = "another.metadata.service"
    os.environ[environment_vars.GCE_METADATA_ROOT] = fake_root
    importlib.reload(_metadata)

    try:
        _metadata.get(request, PATH)
    finally:
        del os.environ[environment_vars.GCE_METADATA_ROOT]
        importlib.reload(_metadata)

    request.assert_called_once_with(
        method="GET",
        url="http://{}/computeMetadata/v1/{}".format(fake_root, PATH),
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


@mock.patch("time.sleep", return_value=None)
def test_get_failure(mock_sleep):
    request = make_request("Metadata error", status=http_client.NOT_FOUND)

    with pytest.raises(exceptions.TransportError) as excinfo:
        _metadata.get(request, PATH)

    assert excinfo.match(r"Metadata error")

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


def test_get_return_none_for_not_found_error():
    request = make_request("Metadata error", status=http_client.NOT_FOUND)

    assert _metadata.get(request, PATH, return_none_for_not_found_error=True) is None

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


@mock.patch("time.sleep", return_value=None)
def test_get_failure_connection_failed(mock_sleep):
    request = make_request("")
    request.side_effect = exceptions.TransportError("failure message")

    with pytest.raises(exceptions.TransportError) as excinfo:
        _metadata.get(request, PATH)

    assert excinfo.match(
        r"Compute Engine Metadata server unavailable due to failure message"
    )

    request.assert_called_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert request.call_count == 5


def test_get_too_many_requests_retryable_error_failure():
    request = make_request("too many requests", status=http_client.TOO_MANY_REQUESTS)

    with pytest.raises(exceptions.TransportError) as excinfo:
        _metadata.get(request, PATH)

    assert excinfo.match(
        r"Compute Engine Metadata server unavailable due to too many requests"
    )

    request.assert_called_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert request.call_count == 5


def test_get_failure_bad_json():
    request = make_request("{", headers={"content-type": "application/json"})

    with pytest.raises(exceptions.TransportError) as excinfo:
        _metadata.get(request, PATH)

    assert excinfo.match(r"invalid JSON")

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH,
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


def test_get_project_id():
    project = "example-project"
    request = make_request(project, headers={"content-type": "text/plain"})

    project_id = _metadata.get_project_id(request)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "project/project-id",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert project_id == project


def test_get_universe_domain_success():
    request = make_request(
        "fake_universe_domain", headers={"content-type": "text/plain"}
    )

    universe_domain = _metadata.get_universe_domain(request)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "universe/universe-domain",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert universe_domain == "fake_universe_domain"


def test_get_universe_domain_success_empty_response():
    request = make_request("", headers={"content-type": "text/plain"})

    universe_domain = _metadata.get_universe_domain(request)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "universe/universe-domain",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert universe_domain == "googleapis.com"


def test_get_universe_domain_not_found():
    # Test that if the universe domain endpoint returns 404 error, we should
    # use googleapis.com as the universe domain
    request = make_request("not found", status=http_client.NOT_FOUND)

    universe_domain = _metadata.get_universe_domain(request)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "universe/universe-domain",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert universe_domain == "googleapis.com"


def test_get_universe_domain_retryable_error_failure():
    # Test that if the universe domain endpoint returns a retryable error
    # we should retry.
    #
    # In this case, the error persists, and we still fail after retrying.
    request = make_request("too many requests", status=http_client.TOO_MANY_REQUESTS)

    with pytest.raises(exceptions.TransportError) as excinfo:
        _metadata.get_universe_domain(request)

    assert excinfo.match(r"Compute Engine Metadata server unavailable")

    request.assert_called_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "universe/universe-domain",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert request.call_count == 5


def test_get_universe_domain_retryable_error_success():
    # Test that if the universe domain endpoint returns a retryable error
    # we should retry.
    #
    # In this case, the error is temporary, and we succeed after retrying.
    request_error = make_request(
        "too many requests", status=http_client.TOO_MANY_REQUESTS
    )
    request_ok = make_request(
        "fake_universe_domain", headers={"content-type": "text/plain"}
    )

    class _RequestErrorOnce:
        """This class forwards the request parameters to `request_error` once.

        All subsequent calls are forwarded to `request_ok`.
        """

        def __init__(self, request_error, request_ok):
            self._request_error = request_error
            self._request_ok = request_ok
            self._call_index = 0

        def request(self, *args, **kwargs):
            if self._call_index == 0:
                self._call_index += 1
                return self._request_error(*args, **kwargs)

            return self._request_ok(*args, **kwargs)

    request = _RequestErrorOnce(request_error, request_ok).request

    universe_domain = _metadata.get_universe_domain(request)

    request_error.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "universe/universe-domain",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    request_ok.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "universe/universe-domain",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )

    assert universe_domain == "fake_universe_domain"


def test_get_universe_domain_other_error():
    # Test that if the universe domain endpoint returns an error other than 404
    # we should throw the error
    request = make_request("unauthorized", status=http_client.UNAUTHORIZED)

    with pytest.raises(exceptions.TransportError) as excinfo:
        _metadata.get_universe_domain(request)

    assert excinfo.match(r"unauthorized")

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + "universe/universe-domain",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )


@mock.patch(
    "google.auth.metrics.token_request_access_token_mds",
    return_value=ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
)
@mock.patch("google.auth._helpers.utcnow", return_value=datetime.datetime.min)
def test_get_service_account_token(utcnow, mock_metrics_header_value):
    ttl = 500
    request = make_request(
        json.dumps({"access_token": "token", "expires_in": ttl}),
        headers={"content-type": "application/json"},
    )

    token, expiry = _metadata.get_service_account_token(request)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH + "/token",
        headers={
            "metadata-flavor": "Google",
            "x-goog-api-client": ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
        },
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert token == "token"
    assert expiry == utcnow() + datetime.timedelta(seconds=ttl)


@mock.patch(
    "google.auth.metrics.token_request_access_token_mds",
    return_value=ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
)
@mock.patch("google.auth._helpers.utcnow", return_value=datetime.datetime.min)
def test_get_service_account_token_with_scopes_list(utcnow, mock_metrics_header_value):
    ttl = 500
    request = make_request(
        json.dumps({"access_token": "token", "expires_in": ttl}),
        headers={"content-type": "application/json"},
    )

    token, expiry = _metadata.get_service_account_token(request, scopes=["foo", "bar"])

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH + "/token" + "?scopes=foo%2Cbar",
        headers={
            "metadata-flavor": "Google",
            "x-goog-api-client": ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
        },
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert token == "token"
    assert expiry == utcnow() + datetime.timedelta(seconds=ttl)


@mock.patch(
    "google.auth.metrics.token_request_access_token_mds",
    return_value=ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
)
@mock.patch("google.auth._helpers.utcnow", return_value=datetime.datetime.min)
def test_get_service_account_token_with_scopes_string(
    utcnow, mock_metrics_header_value
):
    ttl = 500
    request = make_request(
        json.dumps({"access_token": "token", "expires_in": ttl}),
        headers={"content-type": "application/json"},
    )

    token, expiry = _metadata.get_service_account_token(request, scopes="foo,bar")

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH + "/token" + "?scopes=foo%2Cbar",
        headers={
            "metadata-flavor": "Google",
            "x-goog-api-client": ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
        },
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )
    assert token == "token"
    assert expiry == utcnow() + datetime.timedelta(seconds=ttl)


def test_get_service_account_info():
    key, value = "foo", "bar"
    request = make_request(
        json.dumps({key: value}), headers={"content-type": "application/json"}
    )

    info = _metadata.get_service_account_info(request)

    request.assert_called_once_with(
        method="GET",
        url=_metadata._METADATA_ROOT + PATH + "/?recursive=true",
        headers=_metadata._METADATA_HEADERS,
        timeout=_metadata._METADATA_DEFAULT_TIMEOUT,
    )

    assert info[key] == value
