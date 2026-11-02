"""Merriam-Webster lookups are paused in production (config.py). The tests of the
lookup order exercise the code behind that switch, so they run with it on; the
tests of the pause turn it off themselves."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def _mw_lookups_on(monkeypatch):
    import scripts.dictionary_api as dictionary_api

    monkeypatch.setattr(dictionary_api, "MW_LOOKUPS_ENABLED", True)
