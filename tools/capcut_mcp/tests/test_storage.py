import json
from pathlib import Path

import pytest

from capcut_mcp.draft import US, Draft
from capcut_mcp.storage import (DraftError, default_drafts_dir, inspect_draft, list_drafts,
                                save_draft)


def simple_draft(assets, name="Da Lat morning"):
    d = Draft(name)
    d.add_media(assets["img"], duration=3)
    d.add_text("Da Lat at 6 AM", start=0, duration=3)
    return d


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def test_new_folder(tmp_path, assets):
    root = tmp_path / "com.lveditor.draft"
    d = simple_draft(assets)
    res = save_draft(d, str(root))
    folder = Path(res["folder"])
    assert folder == root / "Da Lat morning" and res["mode"] == "new"
    content = load(folder / "draft_content.json")
    meta = load(folder / "draft_meta_info.json")
    assert load(folder / "draft_info.json") == content
    assert content["id"] == meta["draft_id"] == d.id
    assert meta["draft_name"] == "Da Lat morning"
    assert meta["tm_duration"] == content["duration"] == 3 * US
    assert meta["draft_root_path"] == str(root)
    with pytest.raises(DraftError, match="already exists"):
        save_draft(simple_draft(assets), str(root))
    res2 = save_draft(simple_draft(assets), str(root), overwrite=True)
    assert any("moved to" in w for w in res2["warnings"])


def test_unsafe_name_sanitised(tmp_path, assets):
    res = save_draft(simple_draft(assets, name='a/b:c*?'), str(tmp_path))
    assert Path(res["folder"]).name == "a_b_c__"


def make_capcut_project(root: Path, name="1122", app_version="9.3.0"):
    """Imitate an empty project created by a newer CapCut build."""
    folder = root / name
    tl = folder / "Timelines" / "TL-1"
    tl.mkdir(parents=True)
    content = {
        "id": "APP-MADE-ID", "version": 520000, "new_version": "150.0.0", "name": name,
        "platform": {"app_source": "cc", "app_version": app_version, "os": "mac"},
        "last_modified_platform": {"app_source": "cc", "app_version": app_version},
        "materials": {"videos": [], "future_kind": [], "some_setting": {"a": 1}},
        "keyframes": {"videos": [], "future_kf": []}, "tracks": [], "duration": 0,
        "config": {"maintrack_adsorb": False, "future_cfg": 1}, "unknown_top_level": "keep me",
    }
    for p in (folder / "draft_content.json", tl / "draft_content.json"):
        p.write_text(json.dumps(content))
    meta = {"draft_id": "APP-MADE-ID", "draft_name": name, "tm_duration": 0,
            "tm_draft_modified": 1, "draft_fold_path": str(folder), "app_field": True}
    (folder / "draft_meta_info.json").write_text(json.dumps(meta))
    return folder


def test_into_existing_keeps_app_fields(tmp_path, assets):
    root = tmp_path / "drafts"
    folder = make_capcut_project(root)
    d = simple_draft(assets)
    res = save_draft(d, str(root), into_existing="1122")
    assert res["mode"] == "into_existing" and res["draft_id"] == "APP-MADE-ID"
    c = load(folder / "draft_content.json")
    assert c["id"] == "APP-MADE-ID" and c["version"] == 520000
    assert c["platform"]["app_version"] == "9.3.0" and c["name"] == "1122"
    assert c["unknown_top_level"] == "keep me"
    assert c["config"]["future_cfg"] == 1
    assert c["materials"]["future_kind"] == [] and c["materials"]["some_setting"] == {"a": 1}
    assert len(c["materials"]["videos"]) == 1 and len(c["tracks"]) == 2
    assert "future_kf" in c["keyframes"]
    # mirrored into the Timelines/ copy used by CapCut 8.7+/9.x
    assert load(folder / "Timelines" / "TL-1" / "draft_content.json")["tracks"] == c["tracks"]
    meta = load(folder / "draft_meta_info.json")
    assert meta["tm_duration"] == 3 * US and meta["app_field"] is True
    assert list(folder.glob("draft_content.json.bak-*"))
    assert list(folder.glob("draft_meta_info.json.bak-*"))


def test_into_existing_by_name_lookup(tmp_path, assets):
    root = tmp_path / "drafts"
    make_capcut_project(root, name="folder-x")
    meta_p = root / "folder-x" / "draft_meta_info.json"
    meta = json.loads(meta_p.read_text())
    meta["draft_name"] = "My Trip"
    meta_p.write_text(json.dumps(meta))
    res = save_draft(simple_draft(assets), str(root), into_existing="My Trip")
    assert Path(res["folder"]).name == "folder-x"


def test_encrypted_draft_refused(tmp_path, assets):
    root = tmp_path / "drafts"
    folder = root / "jy"
    folder.mkdir(parents=True)
    (folder / "draft_content.json").write_bytes(b"\x8a\x01\xff binary aes blob")
    (folder / "draft_meta_info.json").write_text("{}")
    with pytest.raises(DraftError, match="encrypted"):
        save_draft(simple_draft(assets), str(root), into_existing="jy")


def test_missing_media_blocks_save(tmp_path, assets):
    d = Draft("m")
    d.add_media(assets["clip"], info=assets["clip_info"])
    Path(assets["clip"]).unlink()
    with pytest.raises(DraftError, match="missing"):
        save_draft(d, str(tmp_path))
    res = save_draft(d, str(tmp_path), allow_missing_media=True)
    assert any("missing" in w for w in res["warnings"])


def test_copy_media(tmp_path, assets):
    d = simple_draft(assets)
    d.add_audio(assets["voice"], info=assets["voice_info"])
    res = save_draft(d, str(tmp_path / "drafts"), copy_media=True)
    c = load(Path(res["folder"]) / "draft_content.json")
    paths = [m["path"] for m in c["materials"]["videos"] + c["materials"]["audios"]]
    assert all(Path(p).parent == Path(res["folder"]) / "materials" for p in paths)
    assert all(Path(p).exists() for p in paths)


def test_list_and_inspect(tmp_path, assets):
    root = tmp_path / "drafts"
    d = Draft("with transition")
    d.add_media(assets["img"], duration=2)
    d.add_media(assets["img"], duration=2)
    d.add_transition("main", 0, "Dissolve", "E1", "R1")
    save_draft(d, str(root))
    rows = list_drafts(str(root))
    assert rows[0]["name"] == "with transition" and rows[0]["duration"] == 4.0
    assert rows[0]["readable"] is True
    info = inspect_draft("with transition", str(root))
    assert info["reusable"]["transitions"][0]["resource_id"] == "R1"
    assert [s["material"] for s in info["tracks"][0]["segments"]] == ["videos", "videos"]


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("CAPCUT_DRAFTS_DIR", str(tmp_path))
    assert default_drafts_dir() == tmp_path
