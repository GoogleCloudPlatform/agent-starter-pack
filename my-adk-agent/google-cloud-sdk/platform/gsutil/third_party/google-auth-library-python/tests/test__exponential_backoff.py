# Copyright 2022 Google Inc.
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

import mock
import pytest  # type: ignore

from google.auth import _exponential_backoff
from google.auth import exceptions


@mock.patch("time.sleep", return_value=None)
def test_exponential_backoff(mock_time):
    eb = _exponential_backoff.ExponentialBackoff()
    curr_wait = eb._current_wait_in_seconds
    iteration_count = 0

    for attempt in eb:
        if attempt == 1:
            assert mock_time.call_count == 0
        else:
            backoff_interval = mock_time.call_args[0][0]
            jitter = curr_wait * eb._randomization_factor

            assert (curr_wait - jitter) <= backoff_interval <= (curr_wait + jitter)
            assert attempt == iteration_count + 1
            assert eb.backoff_count == iteration_count + 1
            assert eb._current_wait_in_seconds == eb._multiplier ** iteration_count

            curr_wait = eb._current_wait_in_seconds
        iteration_count += 1

    assert eb.total_attempts == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS
    assert eb.backoff_count == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS
    assert iteration_count == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS
    assert (
        mock_time.call_count == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS - 1
    )


def test_minimum_total_attempts():
    with pytest.raises(exceptions.InvalidValue):
        _exponential_backoff.ExponentialBackoff(total_attempts=0)
    with pytest.raises(exceptions.InvalidValue):
        _exponential_backoff.ExponentialBackoff(total_attempts=-1)
    _exponential_backoff.ExponentialBackoff(total_attempts=1)


@pytest.mark.asyncio
@mock.patch("asyncio.sleep", return_value=None)
async def test_exponential_backoff_async(mock_time_async):
    eb = _exponential_backoff.AsyncExponentialBackoff()
    curr_wait = eb._current_wait_in_seconds
    iteration_count = 0

    # Workaround issue in python 3.9 related to code coverage by adding `# pragma: no branch`
    # See https://github.com/googleapis/gapic-generator-python/pull/1174#issuecomment-1025132372
    async for attempt in eb:  # pragma: no branch
        if attempt == 1:
            assert mock_time_async.call_count == 0
        else:
            backoff_interval = mock_time_async.call_args[0][0]
            jitter = curr_wait * eb._randomization_factor

            assert (curr_wait - jitter) <= backoff_interval <= (curr_wait + jitter)
            assert attempt == iteration_count + 1
            assert eb.backoff_count == iteration_count + 1
            assert eb._current_wait_in_seconds == eb._multiplier ** iteration_count

            curr_wait = eb._current_wait_in_seconds
        iteration_count += 1

    assert eb.total_attempts == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS
    assert eb.backoff_count == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS
    assert iteration_count == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS
    assert (
        mock_time_async.call_count
        == _exponential_backoff._DEFAULT_RETRY_TOTAL_ATTEMPTS - 1
    )


def test_minimum_total_attempts_async():
    with pytest.raises(exceptions.InvalidValue):
        _exponential_backoff.AsyncExponentialBackoff(total_attempts=0)
    with pytest.raises(exceptions.InvalidValue):
        _exponential_backoff.AsyncExponentialBackoff(total_attempts=-1)
    _exponential_backoff.AsyncExponentialBackoff(total_attempts=1)
