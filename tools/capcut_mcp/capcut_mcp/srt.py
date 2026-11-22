"""Minimal SRT parser (no dependencies)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TS = re.compile(
    r"(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})"
)


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_srt(text: str) -> list[Cue]:
    """Parse SRT text into cues. Index lines are optional; blank lines separate cues."""
    cues: list[Cue] = []
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip().lstrip("﻿"))
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip() != ""]
        for i, line in enumerate(lines):
            m = _TS.search(line)
            if m:
                g = m.groups()
                start, end = _sec(*g[:4]), _sec(*g[4:])
                body = "\n".join(lines[i + 1:]).strip()
                body = re.sub(r"<[^>]+>", "", body)  # drop <i>, <b>, <font> tags
                if body and end > start:
                    cues.append(Cue(start, end, body))
                break
    return cues
