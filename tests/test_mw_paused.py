"""With Merriam-Webster lookups paused, the nightly asks the Free Dictionary API
and nothing else, and a refusal still means "not checked tonight"."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import scripts.dictionary_api as dictionary_api
from scripts.dictionary_api import (
    DictionaryAPIClient,
    MerriamWebsterAPI,
    MerriamWebsterMedicalAPI,
    ResponseCache,
    WordLookupResult,
    WordStatus,
)


class FakeSource:
    def __init__(self, status=WordStatus.NOT_FOUND, http_status=None):
        self.status = status
        self.http_status = http_status
        self.asked: list[str] = []
        self.is_configured = True

    async def lookup_word(self, word: str) -> WordLookupResult:
        self.asked.append(word)
        return WordLookupResult(word=word, status=self.status, http_status=self.http_status)


def client(collegiate, medical, free):
    c = DictionaryAPIClient.__new__(DictionaryAPIClient)
    c.mw, c.mw_medical, c.free_dict, c.refused = collegiate, medical, free, {}
    return c


def run(coro):
    return asyncio.run(coro)


def pause(monkeypatch):
    monkeypatch.setattr(dictionary_api, "MW_LOOKUPS_ENABLED", False)


def test_a_paused_night_never_asks_merriam_webster(monkeypatch):
    pause(monkeypatch)
    mw, medical, free = FakeSource(), FakeSource(), FakeSource(WordStatus.VALID)
    result = run(client(mw, medical, free).lookup_word("steamship"))
    assert result.status == WordStatus.VALID
    assert mw.asked == [] and medical.asked == []
    assert free.asked == ["steamship"]


def test_a_paused_night_keeps_a_free_dictionary_not_found(monkeypatch):
    pause(monkeypatch)
    result = run(client(FakeSource(), FakeSource(), FakeSource(WordStatus.NOT_FOUND)).lookup_word("zzzz"))
    assert result.status == WordStatus.NOT_FOUND


def test_a_refusal_by_the_free_dictionary_leaves_the_word_unchecked(monkeypatch):
    pause(monkeypatch)
    free = FakeSource(WordStatus.ERROR, http_status=403)
    c = client(FakeSource(), FakeSource(), free)
    first = run(c.lookup_word("steamship"))
    second = run(c.lookup_word("horrid"))
    assert not first.checked and not second.checked
    assert free.asked == ["steamship"]  # asked once, then not again tonight


def test_the_merriam_webster_clients_make_no_request_while_paused(monkeypatch):
    pause(monkeypatch)
    for api in (
        MerriamWebsterAPI(api_key="x", cache=ResponseCache("t", enabled=False)),
        MerriamWebsterMedicalAPI(api_key="x", cache=ResponseCache("t", enabled=False)),
    ):
        result = run(api.lookup_word("steamship"))
        assert result.status == WordStatus.ERROR
        assert "paused" in result.error_message


def test_switched_back_on_the_collegiate_runs_first(monkeypatch):
    mw, free = FakeSource(WordStatus.VALID), FakeSource()
    result = run(client(mw, FakeSource(), free).lookup_word("steamship"))
    assert result.status == WordStatus.VALID and mw.asked == ["steamship"] and free.asked == []


def test_a_paused_night_that_checks_nothing_still_exits_zero(monkeypatch):
    from scripts.validate_invalid_list import exit_code
    results = {"success": True, "selected": 4, "validated": 0, "not_checked": 4}
    pause(monkeypatch)
    assert exit_code(results) == 0
    monkeypatch.setattr(dictionary_api, "MW_LOOKUPS_ENABLED", True)
    assert exit_code(results) == 1
