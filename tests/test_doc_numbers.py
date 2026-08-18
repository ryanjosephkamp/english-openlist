"""PROTOCOL §9 mechanism 1, as a test: the governance documents may not quote
figures the pinned data does not support. Skips when the data layer is absent
(clean checkout); on the working machine it runs on every pytest invocation,
which is the whole point — drift fails the suite the day it happens."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research import verify_doc_numbers as vdn  # noqa: E402


def test_documents_quote_only_derivable_figures():
    if not vdn.data_available():
        pytest.skip("data layer not present; run after Phase 1 ingest")
    assert vdn.main() == 0, "a governance document quotes a stale figure"
