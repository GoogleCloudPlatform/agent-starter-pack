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

import asyncio
from typing import AsyncGenerator

from aioresponses import aioresponses  # type: ignore
from mock import Mock, patch
import pytest  # type: ignore

from google.auth.aio.credentials import AnonymousCredentials
from google.auth.aio.transport import (
    _DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_MAX_RETRY_ATTEMPTS,
    DEFAULT_RETRYABLE_STATUS_CODES,
    Request,
    Response,
    sessions,
)
from google.auth.exceptions import InvalidType, TimeoutError, TransportError


@pytest.fixture
async def simple_async_task():
    return True


class MockRequest(Request):
    def __init__(self, response=None, side_effect=None):
        self._closed = False
        self._response = response
        self._side_effect = side_effect
        self.call_count = 0

    async def __call__(
        self,
        url,
        method="GET",
        body=None,
        headers=None,
        timeout=_DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ):
        self.call_count += 1
        if self._side_effect:
            raise self._side_effect
        return self._response

    async def close(self):
        self._closed = True
        return None


class MockResponse(Response):
    def __init__(self, status_code, headers=None, content=None):
        self._status_code = status_code
        self._headers = headers
        self._content = content
        self._close = False

    @property
    def status_code(self):
        return self._status_code

    @property
    def headers(self):
        return self._headers

    async def read(self) -> bytes:
        content = await self.content(1024)
        return b"".join([chunk async for chunk in content])

    async def content(self, chunk_size=None) -> AsyncGenerator:
        return self._content

    async def close(self) -> None:
        self._close = True


class TestTimeoutGuard(object):
    default_timeout = 1

    def make_timeout_guard(self, timeout):
        return sessions.timeout_guard(timeout)

    @pytest.mark.asyncio
    async def test_timeout_with_simple_async_task_within_bounds(
        self, simple_async_task
    ):
        task = False
        with patch("time.monotonic", side_effect=[0, 0.25, 0.75]):
            with patch("asyncio.wait_for", lambda coro, _: coro):
                async with self.make_timeout_guard(
                    timeout=self.default_timeout
                ) as with_timeout:
                    task = await with_timeout(simple_async_task)

        # Task succeeds.
        assert task is True

    @pytest.mark.asyncio
    async def test_timeout_with_simple_async_task_out_of_bounds(
        self, simple_async_task
    ):
        task = False
        with patch("time.monotonic", side_effect=[0, 1, 1]):
            with pytest.raises(TimeoutError) as exc:
                async with self.make_timeout_guard(
                    timeout=self.default_timeout
                ) as with_timeout:
                    task = await with_timeout(simple_async_task)

        # Task does not succeed and the context manager times out i.e. no remaining time left.
        assert task is False
        assert exc.match(
            f"Context manager exceeded the configured timeout of {self.default_timeout}s."
        )

    @pytest.mark.asyncio
    async def test_timeout_with_async_task_timing_out_before_context(
        self, simple_async_task
    ):
        task = False
        with pytest.raises(TimeoutError) as exc:
            async with self.make_timeout_guard(
                timeout=self.default_timeout
            ) as with_timeout:
                with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                    task = await with_timeout(simple_async_task)

        # Task does not complete i.e. the operation times out.
        assert task is False
        assert exc.match(
            f"The operation {simple_async_task} exceeded the configured timeout of {self.default_timeout}s."
        )


class TestAsyncAuthorizedSession(object):
    TEST_URL = "http://example.com/"
    credentials = AnonymousCredentials()

    @pytest.fixture
    async def mocked_content(self):
        content = [b"Cavefish ", b"have ", b"no ", b"sight."]
        for chunk in content:
            yield chunk

    @pytest.mark.asyncio
    async def test_constructor_with_default_auth_request(self):
        with patch("google.auth.aio.transport.sessions.AIOHTTP_INSTALLED", True):
            authed_session = sessions.AsyncAuthorizedSession(self.credentials)
        assert authed_session._credentials == self.credentials
        await authed_session.close()

    @pytest.mark.asyncio
    async def test_constructor_with_provided_auth_request(self):
        auth_request = MockRequest()
        authed_session = sessions.AsyncAuthorizedSession(
            self.credentials, auth_request=auth_request
        )

        assert authed_session._auth_request is auth_request
        await authed_session.close()

    @pytest.mark.asyncio
    async def test_constructor_raises_no_auth_request_error(self):
        with patch("google.auth.aio.transport.sessions.AIOHTTP_INSTALLED", False):
            with pytest.raises(TransportError) as exc:
                sessions.AsyncAuthorizedSession(self.credentials)

        exc.match(
            "`auth_request` must either be configured or the external package `aiohttp` must be installed to use the default value."
        )

    @pytest.mark.asyncio
    async def test_constructor_raises_incorrect_credentials_error(self):
        credentials = Mock()
        with pytest.raises(InvalidType) as exc:
            sessions.AsyncAuthorizedSession(credentials)

        exc.match(
            f"The configured credentials of type {type(credentials)} are invalid and must be of type `google.auth.aio.credentials.Credentials`"
        )

    @pytest.mark.asyncio
    async def test_request_default_auth_request_success(self):
        with aioresponses() as m:
            mocked_chunks = [b"Cavefish ", b"have ", b"no ", b"sight."]
            mocked_response = b"".join(mocked_chunks)
            m.get(self.TEST_URL, status=200, body=mocked_response)
            authed_session = sessions.AsyncAuthorizedSession(self.credentials)
            response = await authed_session.request("GET", self.TEST_URL)
            assert response.status_code == 200
            assert response.headers == {"Content-Type": "application/json"}
            assert await response.read() == b"Cavefish have no sight."
            await response.close()

        await authed_session.close()

    @pytest.mark.asyncio
    async def test_request_provided_auth_request_success(self, mocked_content):
        mocked_response = MockResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=mocked_content,
        )
        auth_request = MockRequest(mocked_response)
        authed_session = sessions.AsyncAuthorizedSession(self.credentials, auth_request)
        response = await authed_session.request("GET", self.TEST_URL)
        assert response.status_code == 200
        assert response.headers == {"Content-Type": "application/json"}
        assert await response.read() == b"Cavefish have no sight."
        await response.close()
        assert response._close

        await authed_session.close()

    @pytest.mark.asyncio
    async def test_request_raises_timeout_error(self):
        auth_request = MockRequest(side_effect=asyncio.TimeoutError)
        authed_session = sessions.AsyncAuthorizedSession(self.credentials, auth_request)
        with pytest.raises(TimeoutError):
            await authed_session.request("GET", self.TEST_URL)

    @pytest.mark.asyncio
    async def test_request_raises_transport_error(self):
        auth_request = MockRequest(side_effect=TransportError)
        authed_session = sessions.AsyncAuthorizedSession(self.credentials, auth_request)
        with pytest.raises(TransportError):
            await authed_session.request("GET", self.TEST_URL)

    @pytest.mark.asyncio
    async def test_request_max_allowed_time_exceeded_error(self):
        auth_request = MockRequest(side_effect=TransportError)
        authed_session = sessions.AsyncAuthorizedSession(self.credentials, auth_request)
        with patch("time.monotonic", side_effect=[0, 1, 1]):
            with pytest.raises(TimeoutError):
                await authed_session.request("GET", self.TEST_URL, max_allowed_time=1)

    @pytest.mark.parametrize("retry_status", DEFAULT_RETRYABLE_STATUS_CODES)
    @pytest.mark.asyncio
    async def test_request_max_retries(self, retry_status):
        mocked_response = MockResponse(status_code=retry_status)
        auth_request = MockRequest(mocked_response)
        with patch("asyncio.sleep", return_value=None):
            authed_session = sessions.AsyncAuthorizedSession(
                self.credentials, auth_request
            )
            await authed_session.request("GET", self.TEST_URL)
            assert auth_request.call_count == DEFAULT_MAX_RETRY_ATTEMPTS

    @pytest.mark.asyncio
    async def test_http_get_method_success(self):
        expected_payload = b"content is retrieved."
        authed_session = sessions.AsyncAuthorizedSession(self.credentials)
        with aioresponses() as m:
            m.get(self.TEST_URL, status=200, body=expected_payload)
            response = await authed_session.get(self.TEST_URL)
            assert await response.read() == expected_payload
            response = await authed_session.close()

    @pytest.mark.asyncio
    async def test_http_post_method_success(self):
        expected_payload = b"content is posted."
        authed_session = sessions.AsyncAuthorizedSession(self.credentials)
        with aioresponses() as m:
            m.post(self.TEST_URL, status=200, body=expected_payload)
            response = await authed_session.post(self.TEST_URL)
            assert await response.read() == expected_payload
            response = await authed_session.close()

    @pytest.mark.asyncio
    async def test_http_put_method_success(self):
        expected_payload = b"content is retrieved."
        authed_session = sessions.AsyncAuthorizedSession(self.credentials)
        with aioresponses() as m:
            m.put(self.TEST_URL, status=200, body=expected_payload)
            response = await authed_session.put(self.TEST_URL)
            assert await response.read() == expected_payload
            response = await authed_session.close()

    @pytest.mark.asyncio
    async def test_http_patch_method_success(self):
        expected_payload = b"content is retrieved."
        authed_session = sessions.AsyncAuthorizedSession(self.credentials)
        with aioresponses() as m:
            m.patch(self.TEST_URL, status=200, body=expected_payload)
            response = await authed_session.patch(self.TEST_URL)
            assert await response.read() == expected_payload
            response = await authed_session.close()

    @pytest.mark.asyncio
    async def test_http_delete_method_success(self):
        expected_payload = b"content is deleted."
        authed_session = sessions.AsyncAuthorizedSession(self.credentials)
        with aioresponses() as m:
            m.delete(self.TEST_URL, status=200, body=expected_payload)
            response = await authed_session.delete(self.TEST_URL)
            assert await response.read() == expected_payload
            response = await authed_session.close()
