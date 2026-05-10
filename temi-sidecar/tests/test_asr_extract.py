"""Unit tests for ASR text extraction (no FastAPI import)."""

from __future__ import annotations

from adapters.temi import extract_asr_text_from_woz


def test_extract_top_level_text() -> None:
    assert extract_asr_text_from_woz({"event": "onASRCompleted", "text": "  你好  "}) == "你好"


def test_extract_transcript() -> None:
    assert extract_asr_text_from_woz({"transcript": "lab tour"}) == "lab tour"


def test_extract_nested_asr() -> None:
    data = {"event": "onASRCompleted", "asr": {"result": "nested phrase"}}
    assert extract_asr_text_from_woz(data) == "nested phrase"


def test_extract_empty_returns_none() -> None:
    assert extract_asr_text_from_woz({"event": "onASRCompleted"}) is None


def test_extract_list_first_string() -> None:
    assert extract_asr_text_from_woz({"results": ["  first  "]}) == "first"
