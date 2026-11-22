import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from capcut_mcp import server  # noqa: E402


def call(name, args):
    res = asyncio.run(server.mcp.call_tool(name, args))
    assert not res.is_error, res.content
    return json.loads(res.content[0].text)


def test_tools_listed():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert {"create_draft", "add_media", "add_text", "add_subtitles", "add_audio",
            "add_transition", "get_timeline", "save_draft_to_capcut", "list_capcut_drafts",
            "inspect_capcut_draft", "build_video", "remove_segment", "capcut_info"} <= names


def test_step_by_step_flow(tmp_path, assets):
    d = call("create_draft", {"name": "Hoi An lanterns"})
    did = d["draft_id"]
    call("add_media", {"draft_id": did, "path": assets["img"], "duration": 2.5, "zoom_to": 1.1})
    call("add_text", {"draft_id": did, "text": "Hội An", "start": 0, "duration": 2.5, "y": 0.4})
    tl = call("get_timeline", {"draft_id": did})
    assert tl["duration"] == 2.5 and tl["problems"] == []
    saved = call("save_draft_to_capcut", {"draft_id": did, "drafts_dir": str(tmp_path)})
    assert Path(saved["folder"], "draft_content.json").is_file()


def test_errors_are_readable():
    with pytest.raises(ToolError, match="Unknown draft_id"):
        asyncio.run(server.mcp.call_tool("get_timeline", {"draft_id": "nope"}))


def test_build_video_one_call(tmp_path, assets):
    srt = tmp_path / "vi.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nXin chào\n", encoding="utf-8")
    out = call("build_video", {
        "name": "Ha Giang loop",
        "scenes": [
            {"media": assets["img"], "duration": 2, "text": "Ha Giang Loop", "text_y": 0.3},
            {"media": assets["img"], "duration": 3, "fade_out": 0.5},
        ],
        "subtitles_srt": str(srt),
        "save": True, "drafts_dir": str(tmp_path / "drafts"),
    })
    tracks = {t["name"]: t for t in out["timeline"]["tracks"]}
    assert [s["end"] for s in tracks["main"]["segments"]] == [2.0, 5.0]
    assert tracks["text"]["segments"][0]["label"] == "Ha Giang Loop"
    assert len(tracks["subtitles"]["segments"]) == 1
    assert Path(out["saved"]["folder"]).name == "Ha Giang loop"
