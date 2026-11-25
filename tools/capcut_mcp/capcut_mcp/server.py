"""MCP server: lets Claude build CapCut desktop drafts.

Run:  python -m capcut_mcp            (stdio transport, for Claude Desktop / Claude Code)
SDK:  official MCP Python SDK v2 (`mcp` package, MCPServer API).
"""

from __future__ import annotations

import functools
import platform
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import __version__
from .draft import Draft
from .storage import DraftError, default_drafts_dir, inspect_draft, list_drafts, save_draft

INSTRUCTIONS = """Build CapCut desktop projects (drafts) that the user opens and exports in CapCut.
CapCut has no export API: the result is an editable project, not an .mp4.
Workflow: create_draft -> add_media / add_text / add_subtitles / add_audio (or build_video for
one call) -> get_timeline to check -> save_draft. Times are seconds. Positions x/y are in
[-1, 1] with (0,0) = centre and y=-1 = bottom; on 1080x1920 TikTok keep captions between
y=-0.65 and y=0.55 to stay clear of the app UI. Media paths must exist on the machine
running CapCut. For CapCut 8.7+/9.x ask the user to create an empty project in CapCut,
close CapCut, then save with into_existing=<that project's name>. Only use licensed assets."""

mcp = MCPServer(name="capcut", version=__version__, instructions=INSTRUCTIONS)
_drafts: dict[str, Draft] = {}


def tool(fn):
    """Register fn as an MCP tool; expected failures reach Claude as readable errors."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, KeyError, FileNotFoundError, DraftError) as e:
            msg = e.args[0] if isinstance(e, KeyError) and e.args else str(e)
            raise ToolError(msg) from e
    return mcp.tool()(wrapper)


def _get(draft_id: str) -> Draft:
    try:
        return _drafts[draft_id]
    except KeyError:
        raise ValueError(f"Unknown draft_id {draft_id!r}. Open drafts: {list(_drafts)}") from None


@tool
def capcut_info() -> dict:
    """Show where CapCut drafts are saved on this machine and which drafts are open in memory."""
    d = default_drafts_dir()
    return {"server_version": __version__, "os": platform.system(),
            "drafts_dir": str(d) if d else None,
            "drafts_dir_exists": bool(d and d.is_dir()),
            "open_drafts": {k: v.name for k, v in _drafts.items()}}


@tool
def create_draft(name: str, width: int = 1080, height: int = 1920, fps: float = 30.0) -> dict:
    """Start a new in-memory CapCut project. Default canvas is 1080x1920 (TikTok portrait).
    Returns draft_id for the other tools."""
    d = Draft(name, width, height, fps)
    _drafts[d.id] = d
    return {"draft_id": d.id, "name": name, "canvas": [d.width, d.height], "fps": d.fps}


@tool
def add_media(draft_id: str, path: str, start: float | None = None, duration: float | None = None,
              source_start: float = 0.0, track: str = "main", volume: float = 1.0,
              speed: float = 1.0, scale: float = 1.0, x: float = 0.0, y: float = 0.0,
              fade_in: float = 0.0, fade_out: float = 0.0,
              zoom_from: float | None = None, zoom_to: float | None = None) -> dict:
    """Add a video clip or image to a video track. start omitted = right after the track's last
    clip. Video duration defaults to the rest of the file; images to 3 s. source_start trims the
    head of a video. Use another track name (e.g. "overlay") for picture-in-picture.
    fade_in/fade_out (s) fade opacity; zoom_from/zoom_to (e.g. 1.0 -> 1.12) add a slow zoom.
    volume 0 mutes the clip's own sound."""
    return _get(draft_id).add_media(path, start, duration, source_start, track, volume, speed,
                                    scale, x, y, fade_in, fade_out, zoom_from, zoom_to)


@tool
def add_text(draft_id: str, text: str, start: float, duration: float, track: str = "text",
             font_size: float = 8.0, color: str = "#FFFFFF", bold: bool = False,
             align: str = "center", x: float = 0.0, y: float = 0.0,
             stroke_color: str | None = "#000000", background_color: str | None = None,
             max_width: float = 0.82, fade_in: float = 0.0, fade_out: float = 0.0) -> dict:
    """Add a text overlay (title, hook, callout). Colours are #RRGGBB. Overlapping texts need
    different track names. Use \\n for line breaks."""
    return _get(draft_id).add_text(text, start, duration, track, font_size, color, bold,
                                   align=align, x=x, y=y, stroke_color=stroke_color,
                                   background_color=background_color, max_width=max_width,
                                   fade_in=fade_in, fade_out=fade_out)


@tool
def add_subtitles(draft_id: str, srt: str, track: str = "subtitles", offset: float = 0.0,
                  font_size: float = 6.0, color: str = "#FFFFFF", y: float = -0.62,
                  stroke_color: str | None = "#000000", background_color: str | None = None) -> dict:
    """Add subtitles from SRT text or a path to a .srt file. offset shifts every cue (s)."""
    segs = _get(draft_id).add_subtitles(srt, track, offset, font_size, color, y, stroke_color,
                                        background_color)
    return {"track": track, "cues": len(segs), "first": segs[0], "last": segs[-1]}


@tool
def add_audio(draft_id: str, path: str, start: float = 0.0, duration: float | None = None,
              source_start: float = 0.0, track: str = "audio", volume: float = 1.0,
              fade_in: float = 0.0, fade_out: float = 0.0) -> dict:
    """Add a voice-over or music file. Put music on its own track (e.g. "music", volume 0.2)
    so it can run under the voice-over. duration cuts the file; it never loops."""
    return _get(draft_id).add_audio(path, start, duration, source_start, track, volume,
                                    fade_in, fade_out)


@tool
def add_transition(draft_id: str, track: str, after_segment: int, name: str, effect_id: str,
                   resource_id: str, duration: float = 0.5) -> dict:
    """Add a CapCut library transition after segment index `after_segment` (0-based) on a video
    track. effect_id/resource_id must be copied from a real project via inspect_capcut_draft;
    never invent them. For a resource-free effect use fade_in/fade_out on add_media."""
    return _get(draft_id).add_transition(track, after_segment, name, effect_id, resource_id, duration)


@tool
def remove_segment(draft_id: str, segment_id: str) -> dict:
    """Remove one segment (clip, text, audio) from the draft by its segment_id."""
    _get(draft_id).remove_segment(segment_id)
    return {"removed": segment_id}


@tool
def get_timeline(draft_id: str) -> dict:
    """Show the draft's tracks and segments with start/end times, plus validation problems."""
    d = _get(draft_id)
    return d.summary() | {"problems": d.validate()}


@tool
def save_draft_to_capcut(draft_id: str, into_existing: str | None = None,
                         drafts_dir: str | None = None, overwrite: bool = False,
                         copy_media: bool = False, allow_missing_media: bool = False) -> dict:
    """Write the draft into CapCut's projects folder. CapCut must be closed.
    into_existing = name or folder of an empty project the user made in CapCut (recommended for
    CapCut 8.7+/9.x; originals are backed up as *.bak-<time>). Without it a new folder named
    after the draft is created. copy_media copies files into the project's materials/ folder.
    drafts_dir overrides the auto-detected folder (env CAPCUT_DRAFTS_DIR does too)."""
    return save_draft(_get(draft_id), drafts_dir, into_existing, overwrite, copy_media,
                      allow_missing_media)


@tool
def list_capcut_drafts(drafts_dir: str | None = None) -> list[dict]:
    """List projects in CapCut's drafts folder (name, duration, last modified)."""
    return list_drafts(drafts_dir)


@tool
def inspect_capcut_draft(project: str, drafts_dir: str | None = None) -> dict:
    """Read an existing CapCut project: its tracks, app version, and reusable library resources
    (transition/effect ids) that add_transition can reuse."""
    return inspect_draft(project, drafts_dir)


@tool
def build_video(name: str, scenes: list[dict[str, Any]], voiceover: str | None = None,
                music: str | None = None, music_volume: float = 0.2, subtitles_srt: str | None = None,
                width: int = 1080, height: int = 1920, fps: float = 30.0,
                save: bool = False, into_existing: str | None = None,
                drafts_dir: str | None = None, copy_media: bool = False) -> dict:
    """Build a whole video in one call. scenes is an ordered list; each scene:
    {"media": path, "duration": s (optional for videos), "source_start": s, "volume": 0-1,
     "fade_in": s, "fade_out": s, "zoom_from": 1.0, "zoom_to": 1.1,
     "text": "on-screen caption", "text_y": -0.3, "text_size": 8, "text_color": "#FFFFFF"}.
    Scenes play back to back on the main track. voiceover/music are audio paths; music is
    trimmed to the video length with a 1 s fade out. subtitles_srt is SRT text or a .srt path.
    save=true also writes it to CapCut (see save_draft_to_capcut). Returns draft_id + timeline."""
    if not scenes:
        raise ValueError("scenes is empty")
    d = Draft(name, width, height, fps)
    for i, sc in enumerate(scenes):
        if "media" not in sc:
            raise ValueError(f"scene {i} has no media")
        seg = d.add_media(sc["media"], duration=sc.get("duration"),
                          source_start=sc.get("source_start", 0.0), volume=sc.get("volume", 1.0),
                          fade_in=sc.get("fade_in", 0.0), fade_out=sc.get("fade_out", 0.0),
                          zoom_from=sc.get("zoom_from"), zoom_to=sc.get("zoom_to"))
        if sc.get("text"):
            d.add_text(sc["text"], start=seg["start"], duration=seg["end"] - seg["start"],
                       y=sc.get("text_y", 0.0), font_size=sc.get("text_size", 8.0),
                       color=sc.get("text_color", "#FFFFFF"), bold=sc.get("text_bold", True))
    video_end = d.duration_us / 1_000_000
    if voiceover:
        d.add_audio(voiceover, start=0.0, track="voiceover")
    if music:
        d.add_audio(music, start=0.0, duration=video_end, track="music", volume=music_volume,
                    fade_out=min(1.0, video_end / 2))
    if subtitles_srt:
        d.add_subtitles(subtitles_srt)
    _drafts[d.id] = d
    result: dict[str, Any] = {"draft_id": d.id, "timeline": d.summary(), "problems": d.validate()}
    if save:
        result["saved"] = save_draft(d, drafts_dir, into_existing, copy_media=copy_media)
    return result


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
