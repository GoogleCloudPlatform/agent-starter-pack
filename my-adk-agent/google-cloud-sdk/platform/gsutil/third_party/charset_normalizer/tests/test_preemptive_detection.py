from __future__ import annotations

import pytest

from charset_normalizer import CharsetMatch
from charset_normalizer.utils import any_specified_encoding


@pytest.mark.parametrize(
    "payload, expected_encoding",
    [
        (b'<?xml version="1.0" encoding="EUC-JP"?>', "euc_jp"),
        (b'<html><head><meta charset="utf-8"></head></html>', "utf_8"),
        (b'<html><head><meta charset="utf-57"></head></html>', None),
        (b"# coding: utf-8", "utf_8"),
        (b'<?xml version="1.0" encoding="UTF-8"?>', "utf_8"),
        (b'<?xml version="1.0" encoding="US-ASCII"?>', "ascii"),
        (b'<?xml version="1.0" encoding="JohaB"?>', "johab"),
        (b'<?xml version="1.0" encoding="ibm037"?>', "cp037"),
        (b"<html><head><meta charset=WINDOWS-1252></head></html>", "cp1252"),
        (b'<html><head><meta charset="WINDOWS-1256"></head></html>', "cp1256"),
    ],
)
def test_detect_most_common_body_encoding(payload, expected_encoding):
    specified_encoding = any_specified_encoding(payload)

    assert (
        specified_encoding == expected_encoding
    ), "Unable to determine properly encoding from given body"


@pytest.mark.parametrize(
    "payload, expected_outcome",
    [
        (
            b'<?xml version="1.0" encoding="EUC-JP"?>',
            b'<?xml version="1.0" encoding="utf-8"?>',
        ),
        (
            b'<html><head><meta charset="utf-8"></head></html>',
            b'<html><head><meta charset="utf-8"></head></html>',
        ),
        (
            b'<html><head><meta charset="utf-57"></head></html>',
            b'<html><head><meta charset="utf-57"></head></html>',
        ),
        (b"# coding: utf-8", b"# coding: utf-8"),
        (
            b'<?xml version="1.0" encoding="UTF-8"?>',
            b'<?xml version="1.0" encoding="UTF-8"?>',
        ),
        (
            b'<?xml version="1.0" encoding="US-ASCII"?>',
            b'<?xml version="1.0" encoding="utf-8"?>',
        ),
        (
            b'<?xml version="1.0" encoding="JohaB"?>',
            b'<?xml version="1.0" encoding="utf-8"?>',
        ),
        (
            b"<html><head><meta charset=WINDOWS-1252></head></html>",
            b"<html><head><meta charset=utf-8></head></html>",
        ),
        (
            b'<html><head><meta charset="WINDOWS-1256"></head></html>',
            b'<html><head><meta charset="utf-8"></head></html>',
        ),
    ],
)
def test_preemptive_mark_replacement(payload, expected_outcome):
    """
    When generating (to Unicode converted) bytes, we want to change any potential declarative charset
    to utf-8. This test that.
    """
    specified_encoding = any_specified_encoding(payload)

    detected_encoding = (
        specified_encoding if specified_encoding is not None else "utf-8"
    )

    m = CharsetMatch(
        payload,
        detected_encoding,
        0.0,
        False,
        [],
        preemptive_declaration=specified_encoding,
    )

    transformed_output = m.output()

    assert transformed_output == expected_outcome
