"""Shared session analysis models for Cursor and Claude CLI corpus tools."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class FileTouch:
    path: str
    turn: int
    tool: str


@dataclass
class TurnSnapshot:
    turn: int
    user_chars: int
    assistant_chars: int
    tool_calls: int
    files_touched: list[str]
    naive_cumulative_chars: int
    synthesizer_est_chars: int
    layer3_est_chars: int
    compaction_would_fire: bool
    naive_delta_chars: int = 0
    synth_delta_chars: int = 0
    # Claude CLI only — real usage from assistant events
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    auto_compact: bool = False


@dataclass
class SessionAnalysis:
    session_id: str
    project_slug: str
    transcript_path: str
    source: str  # "cursor" | "claude-cli"
    user_turns: int
    assistant_messages: int
    tool_calls: int
    unique_files: set[str] = field(default_factory=set)
    tool_names: Counter[str] = field(default_factory=Counter)
    turns: list[TurnSnapshot] = field(default_factory=list)
    file_touches: list[FileTouch] = field(default_factory=list)
    auto_compactions: int = 0

    @property
    def final_naive_chars(self) -> int:
        return self.turns[-1].naive_cumulative_chars if self.turns else 0

    @property
    def final_synth_chars(self) -> int:
        return self.turns[-1].synthesizer_est_chars if self.turns else 0

    @property
    def compression_ratio(self) -> float:
        if self.final_naive_chars <= 0:
            return 0.0
        return 1.0 - (self.final_synth_chars / self.final_naive_chars)

    @property
    def total_input_tokens(self) -> int:
        """Final cumulative input (Claude CLI usage is per-session cumulative on last turn)."""
        if not self.turns:
            return 0
        last = self.turns[-1]
        return last.input_tokens + last.cache_read_tokens + last.cache_write_tokens

    @property
    def total_cache_read(self) -> int:
        if not self.turns:
            return 0
        return self.turns[-1].cache_read_tokens

    @property
    def total_output_tokens(self) -> int:
        if not self.turns:
            return 0
        return self.turns[-1].output_tokens
