from __future__ import annotations

import pickle
from email.errors import MessageDefect
from test import DUMMY_POOL

import pytest

from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool
from urllib3.exceptions import (
    ClosedPoolError,
    ConnectTimeoutError,
    EmptyPoolError,
    HeaderParsingError,
    HostChangedError,
    HTTPError,
    LocationParseError,
    MaxRetryError,
    NewConnectionError,
    ReadTimeoutError,
)


class TestPickle:
    @pytest.mark.parametrize(
        "exception",
        [
            HTTPError(None),
            MaxRetryError(DUMMY_POOL, "", None),
            LocationParseError(""),
            ConnectTimeoutError(None),
            HTTPError("foo"),
            HTTPError("foo", IOError("foo")),
            MaxRetryError(HTTPConnectionPool("localhost"), "/", None),
            LocationParseError("fake location"),
            ClosedPoolError(HTTPConnectionPool("localhost"), ""),
            EmptyPoolError(HTTPConnectionPool("localhost"), ""),
            HostChangedError(HTTPConnectionPool("localhost"), "/", 0),
            ReadTimeoutError(HTTPConnectionPool("localhost"), "/", ""),
        ],
    )
    def test_exceptions(self, exception: Exception) -> None:
        result = pickle.loads(pickle.dumps(exception))
        assert isinstance(result, type(exception))


class TestFormat:
    def test_header_parsing_errors(self) -> None:
        hpe = HeaderParsingError([MessageDefect("defects")], "unparsed_data")

        assert "defects" in str(hpe)
        assert "unparsed_data" in str(hpe)


class TestNewConnectionError:
    def test_pool_property_deprecation_warning(self) -> None:
        err = NewConnectionError(HTTPConnection("localhost"), "test")
        with pytest.warns(DeprecationWarning) as records:
            err_pool = err.pool

        assert err_pool is err.conn
        msg = (
            "The 'pool' property is deprecated and will be removed "
            "in urllib3 v2.1.0. Use 'conn' instead."
        )
        record = records[0]
        assert isinstance(record.message, Warning)
        assert record.message.args[0] == msg
