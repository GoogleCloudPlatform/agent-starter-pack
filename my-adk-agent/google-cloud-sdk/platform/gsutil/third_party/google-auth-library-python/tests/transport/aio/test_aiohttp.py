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

from aioresponses import aioresponses  # type: ignore
from mock import AsyncMock, Mock, patch
import pytest  # type: ignore
import pytest_asyncio  # type: ignore

from google.auth import exceptions
import google.auth.aio.transport.aiohttp as auth_aiohttp


try:
    import aiohttp  # type: ignore
except ImportError as caught_exc:  # pragma: NO COVER
    raise ImportError(
        "The aiohttp library is not installed from please install the aiohttp package to use the aiohttp transport."
    ) from caught_exc


@pytest.fixture
def mock_response():
    response = Mock()
    response.status = 200
    response.headers = {"Content-Type": "application/json", "Content-Length": "100"}
    mock_iterator = AsyncMock()
    mock_iterator.__aiter__.return_value = iter(
        [b"Cavefish ", b"have ", b"no ", b"sight."]
    )
    response.content.iter_chunked = lambda chunk_size: mock_iterator
    response.read = AsyncMock(return_value=b"Cavefish have no sight.")
    response.close = AsyncMock()

    return auth_aiohttp.Response(response)


class TestResponse(object):
    @pytest.mark.asyncio
    async def test_response_status_code(self, mock_response):
        assert mock_response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_headers(self, mock_response):
        assert mock_response.headers["Content-Type"] == "application/json"
        assert mock_response.headers["Content-Length"] == "100"

    @pytest.mark.asyncio
    async def test_response_content(self, mock_response):
        content = b"".join([chunk async for chunk in mock_response.content()])
        assert content == b"Cavefish have no sight."

    @pytest.mark.asyncio
    async def test_response_content_raises_error(self, mock_response):
        with patch.object(
            mock_response._response.content,
            "iter_chunked",
            side_effect=aiohttp.ClientPayloadError,
        ):
            with pytest.raises(exceptions.ResponseError) as exc:
                [chunk async for chunk in mock_response.content()]
            exc.match("Failed to read from the payload stream")

    @pytest.mark.asyncio
    async def test_response_read(self, mock_response):
        content = await mock_response.read()
        assert content == b"Cavefish have no sight."

    @pytest.mark.asyncio
    async def test_response_read_raises_error(self, mock_response):
        with patch.object(
            mock_response._response,
            "read",
            side_effect=aiohttp.ClientResponseError(None, None),
        ):
            with pytest.raises(exceptions.ResponseError) as exc:
                await mock_response.read()
            exc.match("Failed to read the response body.")

    @pytest.mark.asyncio
    async def test_response_close(self, mock_response):
        await mock_response.close()
        mock_response._response.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_response_content_stream(self, mock_response):
        itr = mock_response.content().__aiter__()
        content = []
        try:
            while True:
                chunk = await itr.__anext__()
                content.append(chunk)
        except StopAsyncIteration:
            pass
        assert b"".join(content) == b"Cavefish have no sight."


@pytest.mark.asyncio
class TestRequest:
    @pytest_asyncio.fixture
    async def aiohttp_request(self):
        request = auth_aiohttp.Request()
        yield request
        await request.close()

    async def test_request_call_success(self, aiohttp_request):
        with aioresponses() as m:
            mocked_chunks = [b"Cavefish ", b"have ", b"no ", b"sight."]
            mocked_response = b"".join(mocked_chunks)
            m.get("http://example.com", status=200, body=mocked_response)
            response = await aiohttp_request("http://example.com")
            assert response.status_code == 200
            assert response.headers == {"Content-Type": "application/json"}
            content = b"".join([chunk async for chunk in response.content()])
            assert content == b"Cavefish have no sight."

    async def test_request_call_success_with_provided_session(self):
        mock_session = aiohttp.ClientSession()
        request = auth_aiohttp.Request(mock_session)
        with aioresponses() as m:
            mocked_chunks = [b"Cavefish ", b"have ", b"no ", b"sight."]
            mocked_response = b"".join(mocked_chunks)
            m.get("http://example.com", status=200, body=mocked_response)
            response = await request("http://example.com")
            assert response.status_code == 200
            assert response.headers == {"Content-Type": "application/json"}
            content = b"".join([chunk async for chunk in response.content()])
            assert content == b"Cavefish have no sight."

    async def test_request_call_raises_client_error(self, aiohttp_request):
        with aioresponses() as m:
            m.get("http://example.com", exception=aiohttp.ClientError)

            with pytest.raises(exceptions.TransportError) as exc:
                await aiohttp_request("http://example.com/api")

            exc.match("Failed to send request to http://example.com/api.")

    async def test_request_call_raises_timeout_error(self, aiohttp_request):
        with aioresponses() as m:
            m.get("http://example.com", exception=asyncio.TimeoutError)

            with pytest.raises(exceptions.TimeoutError) as exc:
                await aiohttp_request("http://example.com")

            exc.match("Request timed out after 180 seconds.")

    async def test_request_call_raises_transport_error_for_closed_session(
        self, aiohttp_request
    ):
        with aioresponses() as m:
            m.get("http://example.com", exception=asyncio.TimeoutError)
            aiohttp_request._closed = True
            with pytest.raises(exceptions.TransportError) as exc:
                await aiohttp_request("http://example.com")

            exc.match("session is closed.")
            aiohttp_request._closed = False
