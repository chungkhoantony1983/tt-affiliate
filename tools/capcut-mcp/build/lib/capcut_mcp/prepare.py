"""Common spec preparation for the CapCut draft and the MP4 render.

normalise (defaults + context-aware looks) -> voice (edge-tts for scenes that only have `narration`,
scene length follows the audio) so both outputs get the same timing.
"""

from __future__ import annotations

from typing import Any

from .common import normalise_spec

GAP = 0.25  # silence after each spoken line, same as tt-affiliate render_video


def prepare_spec(spec: dict[str, Any]) -> dict[str, Any]:
    s = normalise_spec(spec)
    gender = None
    for sc in s["scenes"]:
        narration = (sc.get("narration") or "").strip()
        if narration and not sc.get("audio"):
            from . import voice
            gender = gender or s.get("voice_gender") or voice.pick_voice(
                s.get("category", ""), s.get("product_name", "") or s.get("name", ""))
            sc["audio"] = str(voice.synthesize(narration, gender))
        if sc.get("audio"):
            from . import voice
            from .common import fetch_media
            need = voice.audio_seconds(fetch_media(sc["audio"])) + GAP
            if sc["duration"] < need:  # never cut a spoken line short
                old = sc["duration"]
                sc["duration"] = round(need, 3)
                for t in sc["texts"]:
                    if abs(float(t["end"]) - old) < 1e-6:  # only texts that followed the scene length
                        t["end"] = sc["duration"]
    return s
