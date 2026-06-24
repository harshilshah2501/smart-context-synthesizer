"""Tests for Dreaming v4 compaction helpers."""

from __future__ import annotations

from compaction import build_compaction_prompt, extract_pins


def test_extract_pins_strips_and_captures():
    text = "do this\n@synth-remember: React 19 — no ReactDOM.render\nand this"
    pins, cleaned = extract_pins(text)
    assert pins == ["React 19 — no ReactDOM.render"]
    assert "@synth-remember" not in cleaned
    assert "do this" in cleaned
    assert "and this" in cleaned


def test_build_compaction_prompt_excludes_pins_from_ledger_instruction():
    prompt = build_compaction_prompt("old ledger", "turns", pinned=["key fact"])
    assert "do NOT duplicate" in prompt
    assert "key fact" in prompt
    assert "old ledger" in prompt
    assert "turns" in prompt
