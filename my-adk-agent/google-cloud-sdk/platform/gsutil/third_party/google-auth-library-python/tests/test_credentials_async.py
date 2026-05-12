# Copyright 2024 Google LLC
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

import pytest  # type: ignore

from google.auth import exceptions
from google.auth.aio import credentials


class CredentialsImpl(credentials.Credentials):
    pass


def test_credentials_constructor():
    credentials = CredentialsImpl()
    assert not credentials.token


@pytest.mark.asyncio
async def test_before_request():
    credentials = CredentialsImpl()
    request = "water"
    headers = {}
    credentials.token = "orchid"

    # before_request should not affect the value of the token.
    await credentials.before_request(request, "http://example.com", "GET", headers)
    assert credentials.token == "orchid"
    assert headers["authorization"] == "Bearer orchid"
    assert "x-allowed-locations" not in headers

    request = "earth"
    headers = {}

    # Second call shouldn't affect token or headers.
    await credentials.before_request(request, "http://example.com", "GET", headers)
    assert credentials.token == "orchid"
    assert headers["authorization"] == "Bearer orchid"
    assert "x-allowed-locations" not in headers


@pytest.mark.asyncio
async def test_static_credentials_ctor():
    static_creds = credentials.StaticCredentials(token="orchid")
    assert static_creds.token == "orchid"


@pytest.mark.asyncio
async def test_static_credentials_apply_default():
    static_creds = credentials.StaticCredentials(token="earth")
    headers = {}

    await static_creds.apply(headers)
    assert headers["authorization"] == "Bearer earth"

    await static_creds.apply(headers, token="orchid")
    assert headers["authorization"] == "Bearer orchid"


@pytest.mark.asyncio
async def test_static_credentials_before_request():
    static_creds = credentials.StaticCredentials(token="orchid")
    request = "water"
    headers = {}

    # before_request should not affect the value of the token.
    await static_creds.before_request(request, "http://example.com", "GET", headers)
    assert static_creds.token == "orchid"
    assert headers["authorization"] == "Bearer orchid"
    assert "x-allowed-locations" not in headers

    request = "earth"
    headers = {}

    # Second call shouldn't affect token or headers.
    await static_creds.before_request(request, "http://example.com", "GET", headers)
    assert static_creds.token == "orchid"
    assert headers["authorization"] == "Bearer orchid"
    assert "x-allowed-locations" not in headers


@pytest.mark.asyncio
async def test_static_credentials_refresh():
    static_creds = credentials.StaticCredentials(token="orchid")
    request = "earth"

    with pytest.raises(exceptions.InvalidOperation) as exc:
        await static_creds.refresh(request)
    assert exc.match("Static credentials cannot be refreshed.")


@pytest.mark.asyncio
async def test_anonymous_credentials_ctor():
    anon = credentials.AnonymousCredentials()
    assert anon.token is None


@pytest.mark.asyncio
async def test_anonymous_credentials_refresh():
    anon = credentials.AnonymousCredentials()
    request = object()
    with pytest.raises(exceptions.InvalidOperation) as exc:
        await anon.refresh(request)
    assert exc.match("Anonymous credentials cannot be refreshed.")


@pytest.mark.asyncio
async def test_anonymous_credentials_apply_default():
    anon = credentials.AnonymousCredentials()
    headers = {}
    await anon.apply(headers)
    assert headers == {}
    with pytest.raises(ValueError):
        await anon.apply(headers, token="orchid")


@pytest.mark.asyncio
async def test_anonymous_credentials_before_request():
    anon = credentials.AnonymousCredentials()
    request = object()
    method = "GET"
    url = "https://example.com/api/endpoint"
    headers = {}
    await anon.before_request(request, method, url, headers)
    assert headers == {}
