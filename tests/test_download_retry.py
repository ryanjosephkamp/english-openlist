"""
Tests for the Hugging Face download retry logic.

Every historical failure of the daily pipeline was a single HTTP 429 on the
first call of the run, with no retry configured. These tests pin down the two
halves of the fix: that transient failures are retried, and that permanent ones
are *not* -- retrying a bad token or a missing file only fails more slowly, and
burns the rate limit further while it does.
"""

import sys
from pathlib import Path

import pytest
from tenacity import wait_none

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scripts.download_from_huggingface import (  # noqa: E402
    TRANSIENT_STATUS,
    _is_transient,
)


class _Response:
    """Minimal stand-in for the `response` attached to an HfHubHTTPError."""

    def __init__(self, status_code):
        self.status_code = status_code


def _http_error(status_code, message=None):
    error = Exception(message or f"{status_code} error")
    error.response = _Response(status_code)
    return error


@pytest.mark.parametrize("status", sorted(TRANSIENT_STATUS))
def test_transient_statuses_are_retried(status):
    assert _is_transient(_http_error(status)) is True


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422])
def test_permanent_statuses_are_not_retried(status):
    assert _is_transient(_http_error(status)) is False


def test_connection_failures_are_retried():
    assert _is_transient(ConnectionError("connection reset by peer")) is True
    assert _is_transient(TimeoutError("timed out")) is True


def test_rate_limit_detected_from_message_when_response_is_missing():
    # huggingface_hub sometimes raises without a usable response object, which
    # is exactly the shape the real pipeline failures arrived in.
    error = Exception(
        "429 Client Error: Too Many Requests for url: "
        "https://huggingface.co/api/datasets/ryanjosephkamp/english-openlist"
    )
    assert _is_transient(error) is True


def test_ordinary_errors_are_not_retried():
    # The message fallback must stay narrow. If it matched loosely, a genuine
    # failure would be retried until the attempt budget ran out.
    for message in [
        "Repository Not Found",
        "Invalid username or password",
        "local variable referenced before assignment",
        "No such file or directory",
    ]:
        assert _is_transient(Exception(message)) is False, message


def test_response_status_wins_over_message_text():
    # A 404 whose body happens to mention a rate limit must still not retry.
    error = _http_error(404, "not found (unrelated mention of rate limit)")
    assert _is_transient(error) is False


def test_retry_wrapper_gives_up_rather_than_looping_forever():
    """A permanently failing transient error must still terminate."""
    from config import MAX_RETRIES
    from scripts.download_from_huggingface import _retry_transient

    attempts = {"count": 0}

    @_retry_transient
    def always_rate_limited():
        attempts["count"] += 1
        raise _http_error(429)

    # `retry_with` keeps the real predicate and stop condition but drops the
    # backoff, so the test exercises the shipped decorator without sleeping
    # through 35 seconds of production waits.
    with pytest.raises(Exception):
        always_rate_limited.retry_with(wait=wait_none())()

    # MAX_RETRIES is retries; the first attempt sits on top of it.
    assert attempts["count"] == MAX_RETRIES + 1


def test_retry_wrapper_succeeds_once_the_hiccup_passes():
    from scripts.download_from_huggingface import _retry_transient

    attempts = {"count": 0}

    @_retry_transient
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise _http_error(429)
        return "downloaded"

    assert flaky.retry_with(wait=wait_none())() == "downloaded"
    assert attempts["count"] == 2


def test_permanent_failure_is_attempted_exactly_once():
    from scripts.download_from_huggingface import _retry_transient

    attempts = {"count": 0}

    @_retry_transient
    def missing():
        attempts["count"] += 1
        raise _http_error(404)

    with pytest.raises(Exception):
        missing()

    assert attempts["count"] == 1
