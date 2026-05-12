from __future__ import annotations

import platform

import pytest

from charset_normalizer import from_bytes


@pytest.mark.xfail(
    platform.python_version_tuple()[0] == "3"
    and platform.python_version_tuple()[1] == "7",
    reason="Unicode database is too old for this case (Python 3.7)",
)
def test_unicode_edge_case():
    payload = b"\xef\xbb\xbf\xf0\x9f\xa9\xb3"

    best_guess = from_bytes(payload).best()

    assert (
        best_guess is not None
    ), "Payload should have given something, detection failure"
    assert best_guess.encoding == "utf_8", "UTF-8 payload wrongly detected"


def test_issue_gh520():
    """Verify that minorities does not strip basic latin characters!"""
    payload = b"/includes/webform.compon\xd2\xaants.inc/"

    best_guess = from_bytes(payload).best()

    assert (
        best_guess is not None
    ), "Payload should have given something, detection failure"
    assert "Basic Latin" in best_guess.alphabets


def test_issue_gh509():
    """Two common ASCII punctuations should render as-is."""
    payload = b");"

    best_guess = from_bytes(payload).best()

    assert (
        best_guess is not None
    ), "Payload should have given something, detection failure"
    assert "ascii" == best_guess.encoding


def test_issue_gh498():
    """This case was mistaken for utf-16-le, this should never happen again."""
    payload = b"\x84\xae\xaa\xe3\xac\xa5\xad\xe2 Microsoft Word.docx"

    best_guess = from_bytes(payload).best()

    assert (
        best_guess is not None
    ), "Payload should have given something, detection failure"
    assert "Cyrillic" in best_guess.alphabets
