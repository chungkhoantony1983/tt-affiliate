import json

import pytest

from capcut_mcp.draft import US, Draft, hex_to_rgb, utf16_len
from capcut_mcp.srt import parse_srt


def all_material_ids(content):
    return {m["id"] for lst in content["materials"].values() for m in lst}


def build(assets):
    d = Draft("Hanoi in 30s", 1080, 1920, 30)
    d.add_media(assets["clip"], duration=4.0, source_start=2.0, info=assets["clip_info"],
                fade_in=0.5)
    d.add_media(assets["img"], duration=3.0, zoom_from=1.0, zoom_to=1.15, fade_out=0.4)
    d.add_text("Is Hà Giang safe?", start=0.0, duration=2.5, y=0.3, bold=True)
    d.add_audio(assets["voice"], start=0.0, track="voiceover", info=assets["voice_info"])
    d.add_audio(assets["music"], start=0.0, duration=7.0, track="music", volume=0.2,
                fade_out=1.0, info=assets["music_info"])
    return d


def test_timeline_in_microseconds_and_append(assets):
    d = build(assets)
    c = d.to_content()
    main = next(t for t in c["tracks"] if t["name"] == "main")
    s0, s1 = main["segments"]
    assert s0["target_timerange"] == {"start": 0, "duration": 4 * US}
    assert s0["source_timerange"] == {"start": 2 * US, "duration": 4 * US}
    assert s1["target_timerange"] == {"start": 4 * US, "duration": 3 * US}  # appended
    # voice-over (9.5 s) is the longest track
    assert c["duration"] == int(9.5 * US)
    assert c["canvas_config"]["width"] == 1080 and c["canvas_config"]["height"] == 1920
    assert c["fps"] == 30.0


def test_every_reference_resolves(assets):
    c = build(assets).to_content()
    ids = all_material_ids(c)
    for t in c["tracks"]:
        for s in t["segments"]:
            assert s["material_id"] in ids
            for r in s["extra_material_refs"]:
                assert r in ids
    # each segment's material is unique (CapCut expects 1:1)
    mids = [s["material_id"] for t in c["tracks"] for s in t["segments"]]
    assert len(mids) == len(set(mids))
    json.dumps(c)  # serialisable


def test_material_fields(assets):
    c = build(assets).to_content()
    vids = c["materials"]["videos"]
    assert [v["type"] for v in vids] == ["video", "photo"]
    assert vids[0]["duration"] == 12 * US and vids[0]["width"] == 1920
    assert vids[1]["width"] == 64 and vids[1]["height"] == 96  # read from PNG header
    assert all(v["path"].startswith("/") for v in vids)
    assert {a["type"] for a in c["materials"]["audios"]} == {"extract_music"}
    assert len(c["materials"]["audio_fades"]) == 1


def test_text_content_is_json_with_utf16_range(assets):
    d = Draft("t")
    d.add_text("Phở 🍜 ngon", start=0, duration=2, color="#FFCC00", stroke_color=None)
    m = d.to_content()["materials"]["texts"][0]
    content = json.loads(m["content"])
    assert content["text"] == "Phở 🍜 ngon"
    assert content["styles"][0]["range"] == [0, utf16_len("Phở 🍜 ngon")] == [0, 11]
    assert content["styles"][0]["fill"]["content"]["solid"]["color"] == hex_to_rgb("#FFCC00")
    assert "strokes" not in content["styles"][0]


def test_fade_and_zoom_keyframes(assets):
    c = build(assets).to_content()
    main = next(t for t in c["tracks"] if t["name"] == "main")
    alpha0 = main["segments"][0]["common_keyframes"][0]
    assert alpha0["property_type"] == "KFTypeAlpha"
    assert [(k["time_offset"], k["values"][0]) for k in alpha0["keyframe_list"]] == [(0, 0.0), (500000, 1.0)]
    props = {k["property_type"] for k in main["segments"][1]["common_keyframes"]}
    assert props == {"KFTypeAlpha", "KFTypeScaleX", "KFTypeScaleY"}


def test_overlap_rejected_and_other_track_ok(assets):
    d = Draft("o")
    d.add_text("A", start=0, duration=2)
    with pytest.raises(ValueError, match="Overlaps"):
        d.add_text("B", start=1, duration=2)
    d.add_text("B", start=1, duration=2, track="text2")
    assert len(d.tracks) == 2


def test_clip_longer_than_source_rejected(assets):
    d = Draft("x")
    with pytest.raises(ValueError, match="source"):
        d.add_media(assets["clip"], duration=11.0, source_start=2.0, info=assets["clip_info"])


def test_speed_changes_source_range(assets):
    d = Draft("s")
    d.add_media(assets["clip"], speed=2.0, info=assets["clip_info"])
    s = d.to_content()["tracks"][0]["segments"][0]
    assert s["target_timerange"]["duration"] == 6 * US
    assert s["source_timerange"]["duration"] == 12 * US


def test_audio_trimmed_to_available(assets):
    d = Draft("a")
    seg = d.add_audio(assets["voice"], duration=30, info=assets["voice_info"])
    assert seg["end"] == 9.5


def test_wrong_kinds_rejected(assets):
    d = Draft("k")
    with pytest.raises(ValueError):
        d.add_media(assets["voice"])
    with pytest.raises(ValueError):
        d.add_audio(assets["img"])
    with pytest.raises(FileNotFoundError):
        d.add_media("/nope/missing.mp4", duration=2)


def test_subtitles_from_srt():
    srt = """1
00:00:00,000 --> 00:00:02,500
<i>Xin chào</i> Hà Nội

2
00:00:02,500 --> 00:00:05,000
Line one
Line two
"""
    cues = parse_srt(srt)
    assert [(c.start, c.end) for c in cues] == [(0.0, 2.5), (2.5, 5.0)]
    assert cues[0].text == "Xin chào Hà Nội"
    d = Draft("sub")
    d.add_subtitles(srt, offset=1.0)
    c = d.to_content()
    assert all(m["type"] == "subtitle" for m in c["materials"]["texts"])
    starts = [s["target_timerange"]["start"] for s in c["tracks"][0]["segments"]]
    assert starts == [1 * US, int(3.5 * US)]


def test_subtitles_from_file(tmp_path):
    f = tmp_path / "vi.srt"
    f.write_text("1\n00:00:01,000 --> 00:00:02,000\nChào\n", encoding="utf-8")
    d = Draft("f")
    assert len(d.add_subtitles(str(f))) == 1


def test_transition_requires_ids_and_attaches(assets):
    d = Draft("tr")
    d.add_media(assets["img"], duration=2)
    d.add_media(assets["img"], duration=2)
    with pytest.raises(ValueError):
        d.add_transition("main", 0, "Dissolve", "", "")
    d.add_transition("main", 0, "Dissolve", "123", "456", duration=0.6)
    c = d.to_content()
    tr = c["materials"]["transitions"][0]
    assert tr["duration"] == 600000 and tr["resource_id"] == "456"
    assert tr["id"] in c["tracks"][0]["segments"][0]["extra_material_refs"]
    with pytest.raises(ValueError):
        d.add_transition("main", 1, "Dissolve", "1", "2")  # no next segment


def test_remove_segment_garbage_collects(assets):
    d = build(assets)
    seg = d.add_text("bye", start=8, duration=1)
    n = len(d.materials["texts"])
    d.remove_segment(seg["segment_id"])
    assert len(d.materials["texts"]) == n - 1
    assert d.validate() == []


def test_validate_reports_missing_media(assets, tmp_path):
    d = Draft("v")
    assert d.validate() == ["Draft has no segments"]
    d.add_media(assets["clip"], info=assets["clip_info"])
    import os
    os.remove(assets["clip"])
    assert any("Media file missing" in p for p in d.validate())


def test_track_order_video_audio_text(assets):
    c = build(assets).to_content()
    assert [t["type"] for t in c["tracks"]] == ["video", "audio", "audio", "text"]
