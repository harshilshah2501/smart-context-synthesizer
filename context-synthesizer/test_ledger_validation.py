"""Tests for structured L2 ledger validation."""

from __future__ import annotations

from ledger_validation import (
    ArchitectureLedger,
    parse_ledger_bullets,
    strip_markdown_fences,
    validate_and_normalize_ledger,
)


def test_strip_markdown_fences():
    raw = "```markdown\n- database: MongoDB\n- api/client.py: retry policy\n```"
    assert strip_markdown_fences(raw) == "- database: MongoDB\n- api/client.py: retry policy"


def test_state_override_latest_file_path_wins():
    raw = "\n".join(
        [
            "- src/app.py: uses PostgreSQL adapter",
            "- src/app.py: migrated to MongoDB adapter",
            "- database: PostgreSQL",
            "- database: MongoDB",
        ]
    )
    out = validate_and_normalize_ledger(raw)
    assert out.count("src/app.py") == 1
    assert "MongoDB adapter" in out
    assert "PostgreSQL adapter" not in out
    assert "- database: MongoDB" in out
    assert "PostgreSQL" not in out.split("database:")[-1]


def test_classifies_deprecated_and_constraints():
    raw = "\n".join(
        [
            "- ReactDOM.render is deprecated; use createRoot",
            "- API responses must include request_id",
            "- stack: Python/FastAPI",
        ]
    )
    out = validate_and_normalize_ledger(raw)
    assert "deprecated" in out.lower()
    assert "request_id" in out
    assert "- stack: Python/FastAPI" in out


def test_parse_ledger_bullets_multiline():
    raw = "- src/foo.py: first line\n  continuation line\n- other fact"
    bullets = parse_ledger_bullets(raw)
    assert len(bullets) == 2
    assert "continuation line" in bullets[0]


def test_validate_falls_back_when_empty():
    assert validate_and_normalize_ledger("", fallback="prior ledger") == "prior ledger"


def test_validate_keeps_prose_when_no_bullets():
    raw = "Updated architecture notes without bullet markers."
    assert validate_and_normalize_ledger(raw) == raw


def test_architecture_ledger_from_bullets_order_independent_paths():
    ledger = ArchitectureLedger.from_bullets(
        [
            "- /a/x.py: state A",
            "- /b/y.py: state B",
            "- /a/x.py: state A2",
        ]
    )
    text = ledger.to_ledger_text()
    assert ledger.file_state["/a/x.py"].endswith("state A2")
    assert "/b/y.py" in text
