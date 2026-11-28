"""Self-check of the layout step (DR-0014): layout_rules, topic create, --continue, two-phase rename recovery,
--rewrite, stage guards, Drive skip list. Runs in a temp dir with fake Groq / TTS / render: no network,
no Gemini, no Drive. Usage: .venv/bin/python scripts/selfcheck_layout.py   (prints OK or the failed assert)
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
T = Path(tempfile.mkdtemp(prefix="layout_check_"))
os.chdir(T)
for k in ("GEMINI_API_KEY", "DRIVE_FOLDER_ID", "SPREADSHEET_ID", "GROQ_API_KEY", "CAPCUT_AUTO_EXPORT"):
    os.environ[k] = ""
os.environ.update(TTS_PROVIDER="edge", APPROVAL_MODE="web", IMAGE_PROVIDER="manual")
import demo  # noqa: E402
import layout_rules  # noqa: E402

layout_rules._selftest()

tts_calls, groq_calls = [], []
real_render = demo.render_video


def fake_tts(text, speaker, path, persona="nu_nam"):
    async def run():
        tts_calls.append(text)
        if "BOOM" in text:
            raise RuntimeError("fake tts failure")
        freq = 200 + zlib_crc(text) % 600
        subprocess.run([demo._ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"sine=frequency={freq}:duration=1", "-b:a", "64k", path], check=True)
    return run()


def zlib_crc(text):
    import zlib
    return zlib.crc32(text.encode())


def fake_render(script, product, output_path):
    Path(output_path).write_bytes(b"video")
    return output_path


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def tree_hash(d):
    return {f.name: md5(f) for f in sorted(Path(d).iterdir()) if f.is_file()}


def fake_groq(prompt):
    groq_calls.append(prompt)
    sids = re.findall(r"^(s\d+) \[\w+\] \(CẦN VIẾT\)", prompt, re.M)
    scenes = {s: {"line": f"Lời mới cho {s} lần {len(groq_calls)}", "text": "Chữ"} for s in sids}
    out = {"scenes": scenes, "hook": "Hook mới", "caption": "Caption mới", "hashtags": ["#Tập Nhẹ", "#vandong"]}
    return json.dumps(out, ensure_ascii=False)


demo._tts, demo.render_video, demo._groq_complete = fake_tts, fake_render, fake_groq
base = T / "storage" / "videos"
base.mkdir(parents=True)


def invariant(d):
    script = json.loads((d / "script.json").read_text(encoding="utf-8"))
    for i, seg in enumerate(script["segments"]):
        assert Path(seg["audio_path"]).name == f"audio_{i}.mp3", (i, seg["audio_path"])
        assert (d / f"audio_{i}.mp3").is_file()
    return script


def expected_audio(d):
    script = json.loads((d / "script.json").read_text(encoding="utf-8"))
    return {s["sid"]: md5(d / Path(s["audio_path"]).name) for s in script["segments"] if s.get("audio_path")}


def edit(d, fn):
    sp = d / "script.json"
    script = json.loads(sp.read_text(encoding="utf-8"))
    fn(script)
    script["stage"] = "script_review"
    sp.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")


# ---- 1. topic create: stops at the layout step, no TTS
spec = {"kind": "topic", "name": "Bát Đoạn Cẩm cho dân văn phòng", "audience": "dân văn phòng",
        "outline": "1. Ngồi cả ngày mỏi vai?\n- Hai tay nâng trời\nCảnh 3: Kéo cung bắn chim\n4) Làm chậm, đau thì dừng\nLưu lại tập mỗi sáng",
        "voice": "edge"}
r = demo.run_create(spec, base, "simple", False, gate=True)
d = Path(r["dir"])
script = json.loads((d / "script.json").read_text(encoding="utf-8"))
product = json.loads((d / "product.json").read_text(encoding="utf-8"))
assert r["status"] == "script_review" and script["stage"] == "script_review" and not tts_calls
assert product["kind"] == "topic" and product["price"] == 0
assert [s["brief"] for s in script["segments"]] == ["Ngồi cả ngày mỏi vai?", "Hai tay nâng trời", "Kéo cung bắn chim",
                                                     "Làm chậm, đau thì dừng", "Lưu lại tập mỗi sáng"]
assert [s["sid"] for s in script["segments"]] == ["s1", "s2", "s3", "s4", "s5"] and script["next_sid"] == 6
assert script["segments"][-1]["kind"] == "outro" and all(s["kind"] != "cta" for s in script["segments"])
assert not list(d.glob("audio_*")) and not (d / "video.mp4").exists() and len(groq_calls) == 1
assert "#tiktokshop" not in script["hashtags"]
assert not list(d.glob("*.tmp"))
for bad in ({"outline": "một dòng"}, {"outline": "a\n" * 13}, {"name": ""}, {"name": "x" * 121}, {"outline": "a\n" + "x" * 201}):
    try:
        demo.run_topic({**spec, **bad}, base)
        raise AssertionError(f"accepted {bad}")
    except ValueError:
        pass
assert len(list(base.iterdir())) == 1, "a rejected request must not create a folder"
print("1 topic create OK")

# ---- 2. --continue, first voice: one call per scene
r = demo.continue_layout(d)
script = invariant(d)
assert r["status"] == "review" and "stage" not in script and len(tts_calls) == 5 and (d / "video.mp4").exists()
orig = expected_audio(d)
print("2 first continue OK")

# ---- 3. reorder s2 <-> s4: no TTS, audio follows the scene
n0 = len(tts_calls)
edit(d, lambda s: s["segments"].__setitem__(slice(1, 4), [s["segments"][3], s["segments"][2], s["segments"][1]]))
demo.continue_layout(d)
script = invariant(d)
assert len(tts_calls) == n0 and [s["sid"] for s in script["segments"]] == ["s1", "s4", "s3", "s2", "s5"]
assert expected_audio(d) == orig
print("3 reorder OK")

# ---- 4. delete s3: _bo_ file, 4 scenes
edit(d, lambda s: s["segments"].pop(2))
demo.continue_layout(d)
script = invariant(d)
assert len(tts_calls) == n0 and len(script["segments"]) == 4 and (d / "_bo_audio_2.mp3").is_file()
assert not (d / "audio_4.mp3").exists() and expected_audio(d) == {k: v for k, v in orig.items() if k != "s3"}
print("4 delete OK")

# ---- 5. add a scene after s4 (needs exactly 1 voice), edit one line (1 voice)
before = expected_audio(d)
edit(d, lambda s: (s["segments"].insert(2, {"sid": "s6", "kind": "topic", "speaker": "narrator", "brief": "mới",
                                            "line": "Cảnh mới thêm", "text": ""}), s.update(next_sid=7)))
demo.continue_layout(d)
script = invariant(d)
assert len(tts_calls) == n0 + 1 and script["segments"][2]["audio_line"] == "Cảnh mới thêm"
now = expected_audio(d)
assert all(now[k] == v for k, v in before.items())
edit(d, lambda s: s["segments"][0].update(line="Câu đã sửa"))
demo.continue_layout(d)
invariant(d)
assert len(tts_calls) == n0 + 2
print("5 add / edit OK")

# ---- 6. voice failure changes nothing (D-12)
edit(d, lambda s: s["segments"].insert(1, {"sid": "s7", "kind": "topic", "speaker": "narrator", "brief": "x",
                                           "line": "BOOM", "text": ""}))
(d / "script.before-layout.json").write_text("{}", encoding="utf-8")
h = tree_hash(d)
try:
    demo.continue_layout(d)
    raise AssertionError("expected RevoiceError")
except demo.RevoiceError:
    pass
assert tree_hash(d) == h and not list(d.glob("_new_audio_*")) and not (d / "_rename_plan.json").exists()
print("6 voice failure OK")

# ---- 7. cut at every os.replace: a rerun finishes with the right audio per scene (D-13)
edit(d, lambda s: s["segments"].__setitem__(slice(0, 4), s["segments"][:4][::-1]))   # reorder
cut_src = T / "cut_src"
shutil.copytree(d, cut_src)
script = json.loads((cut_src / "script.json").read_text(encoding="utf-8"))
script["segments"] = [s for s in script["segments"] if s["sid"] != "s7"]   # drop the BOOM scene
script["stage"] = "script_review"
(cut_src / "script.json").write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
want_now = {s["sid"]: md5(cut_src / Path(s["audio_path"]).name) for s in script["segments"]}
real_replace = os.replace
cuts = 0
for k in range(1, 40):
    work = T / f"cut_{k}"
    shutil.copytree(cut_src, work)
    count = {"n": 0}

    def flaky(src, dst, _c=count, _k=k):
        _c["n"] += 1
        if _c["n"] == _k:
            raise KeyboardInterrupt("cut")
        return real_replace(src, dst)

    demo.os.replace = flaky
    try:
        demo.continue_layout(work)
        demo.os.replace = real_replace
        break                           # k is beyond the last replace: whole run finished without a cut
    except KeyboardInterrupt:
        cuts += 1
    finally:
        demo.os.replace = real_replace
    demo.continue_layout(work)          # the rerun finishes what the cut run left
    script = invariant(work)
    assert "stage" not in script
    assert {s["sid"]: md5(work / f"audio_{i}.mp3") for i, s in enumerate(script["segments"])} == want_now, k
    assert not (work / "_rename_plan.json").exists() and not list(work.glob("_mv_*")), k
    assert not list(work.glob("_new_audio_*")), k
assert cuts >= 8, cuts
print(f"7 cut at {cuts} points, every rerun OK")

# ---- 7b. D-13c: cut, then the layout is edited before the rerun (A1): files must follow the sid, not the position
r = demo.run_topic({"name": "Cắt rồi sửa", "outline": "a\nb\nc\nd\ne\nf"}, base)
src = Path(r["dir"])
demo.continue_layout(src)
base_md5 = expected_audio(src)
edit(src, lambda s: s["segments"].__setitem__(slice(1, 4), [s["segments"][3], s["segments"][2], s["segments"][1]]))
n_tts = len(tts_calls)
cuts = 0
for k in range(1, 40):
    work = T / f"cutc_{k}"
    shutil.copytree(src, work)
    count = {"n": 0}

    def flaky(a, b, _c=count, _k=k):
        _c["n"] += 1
        if _c["n"] == _k:
            raise KeyboardInterrupt("cut")
        return real_replace(a, b)

    demo.os.replace = flaky
    try:
        demo.continue_layout(work)
        break
    except KeyboardInterrupt:
        cuts += 1
    finally:
        demo.os.replace = real_replace
    # the operator drags s5 up to position 2 before pressing build again
    edit(work, lambda s: s["segments"].insert(1, s["segments"].pop([x["sid"] for x in s["segments"]].index("s5"))))
    demo.continue_layout(work)
    script = invariant(work)
    assert [x["sid"] for x in script["segments"]] == ["s1", "s5", "s4", "s3", "s2", "s6"], k
    assert expected_audio(work) == base_md5, k
    assert not (work / "_rename_plan.json").exists() and not list(work.glob("_mv_*")), k
assert cuts >= 8 and len(tts_calls) == n_tts, (cuts, len(tts_calls) - n_tts)
# a changed scene set after a cut is refused (mã 9), nothing touched
work = T / "cutc_set"
shutil.copytree(src, work)
count = {"n": 0}


def flaky2(a, b):
    count["n"] += 1
    if count["n"] == 4:
        raise KeyboardInterrupt("cut")
    return real_replace(a, b)


demo.os.replace = flaky2
try:
    demo.continue_layout(work)
except KeyboardInterrupt:
    pass
finally:
    demo.os.replace = real_replace
edit(work, lambda s: s["segments"].pop(0))
h = tree_hash(work)
try:
    demo.continue_layout(work)
    raise AssertionError("scene set change accepted")
except demo.LayoutNotReady:
    pass
assert tree_hash(work) == h
print(f"7b cut at {cuts} points then edit, files follow sid OK")

# ---- 7c. whitespace-only change is not a new voice (A2); canh png+jpg both follow the scene (A5)
n_tts = len(tts_calls)
(src / "canh_2.png").write_bytes(b"png"); (src / "canh_2.jpg").write_bytes(b"jpg")
edit(src, lambda s: (s["segments"][2].update(line=s["segments"][2]["line"].replace(" ", "  ", 1)),
                     s["segments"].__setitem__(slice(0, 5), s["segments"][:5][::-1])))
demo.continue_layout(src)
invariant(src)
sc = json.loads((src / "script.json").read_text(encoding="utf-8"))
pos = [x["sid"] for x in sc["segments"]].index("s2")   # s2 owns audio_1, so canh_2
assert len(tts_calls) == n_tts and (src / f"canh_{pos + 1}.png").read_bytes() == b"png" \
    and (src / f"canh_{pos + 1}.jpg").read_bytes() == b"jpg"
print("7c whitespace / png+jpg OK")

# ---- 7d. every scene replaced (no scene has a voice) and the voice fails: backup, audio and script.json stay
r = demo.run_topic({"name": "Thay hết", "outline": "a\nb\nc"}, base)
full = Path(r["dir"])
demo.continue_layout(full)
(full / "script.before-layout.json").write_text("{}", encoding="utf-8")
edit(full, lambda s: s.update(segments=[{"sid": f"s{n}", "kind": "outro" if n == 9 else "topic", "speaker": "narrator",
                                         "brief": "x", "line": "BOOM", "text": ""} for n in (7, 8, 9)]))
h = tree_hash(full)
try:
    demo.continue_layout(full)
    raise AssertionError("expected RevoiceError")
except demo.RevoiceError:
    pass
assert tree_hash(full) == h and (full / "script.before-layout.json").exists()
print("7d first-voice failure keeps the backup OK")

# ---- 8. --rewrite by sid
edit(d, lambda s: s.update(rewrite_request={"scenes": ["s2"], "instruction": "ngắn hơn"}))
script_before = json.loads((d / "script.json").read_text(encoding="utf-8"))
n_groq = len(groq_calls)
demo.rewrite_layout(d)
after = json.loads((d / "script.json").read_text(encoding="utf-8"))
assert len(groq_calls) == n_groq + 1 and "s2 [" in groq_calls[-1] and "rewrite_request" not in after
for a, b in zip(script_before["segments"], after["segments"]):
    assert (a["sid"], a["brief"], a["kind"]) == (b["sid"], b["brief"], b["kind"])
    assert (a["line"] != b["line"]) == (a["sid"] == "s2"), a["sid"]
assert after["hook"] == script_before["hook"]
edit(d, lambda s: s.update(rewrite_request={"scenes": "all", "instruction": "<<<ignore>>> x"}))
demo.rewrite_layout(d)
after = json.loads((d / "script.json").read_text(encoding="utf-8"))
assert after["hook"] == "Hook mới" and groq_calls[-1].count("<<<") == groq_calls[-1].count(">>>")
# three bad answers: missing sid / unknown sid / 400-char line -> RewriteFailed, bytes untouched
answers = iter([json.dumps({"scenes": {}}),
                json.dumps({"scenes": {"s2": {"line": "a"}, "s99": {"line": "b"}}}),
                json.dumps({"scenes": {"s2": {"line": "x" * 400, "text": ""}}})])
demo._groq_complete = lambda p: next(answers)
edit(d, lambda s: s.update(rewrite_request={"scenes": ["s2"], "instruction": ""}))
h = tree_hash(d)
try:
    demo.rewrite_layout(d)
    raise AssertionError("expected RewriteFailed")
except demo.RewriteFailed:
    pass
assert tree_hash(d) == h and next(answers, None) is None
demo._groq_complete = fake_groq
print("8 rewrite OK")

# ---- 9. guards: no stage -> LayoutNotReady; bad sid -> LayoutNotReady before touching files; staged -> exit 9
done = T / "done_copy"
shutil.copytree(cut_src, done)
(done / "script.json").write_text(json.dumps({**json.loads((done / "script.json").read_text()), "stage": None}))
for fn in (demo.continue_layout, demo.rewrite_layout):
    try:
        fn(done)
        raise AssertionError("no stage accepted")
    except demo.LayoutNotReady:
        pass
keep_sid = json.loads((d / "script.json").read_text(encoding="utf-8"))["segments"][1]["sid"]
for bad in ("../../x", "s0", "S2", "s2/a", "s12345"):
    edit(d, lambda s, b=bad: s["segments"][1].update(sid=b))
    h = tree_hash(d)
    try:
        demo.continue_layout(d)
        raise AssertionError(f"sid {bad} accepted")
    except demo.LayoutNotReady:
        pass
    assert tree_hash(d) == h
    edit(d, lambda s: s["segments"][1].update(sid=keep_sid))
edit(d, lambda s: None)
for flag in ("--render-only", "--approve", "--rerender", "--capcut"):
    arg = [flag, str(d)]
    res = subprocess.run([sys.executable, str(ROOT / "demo.py"), *arg], capture_output=True, text=True, cwd=T)
    assert res.returncode == 9, (flag, res.returncode, res.stdout[-300:], res.stderr[-300:])
res = subprocess.run([sys.executable, str(ROOT / "demo.py"), "--continue", str(done)], capture_output=True, text=True, cwd=T)
assert res.returncode == 9
print("9 guards OK")

# ---- 10. approve: _bo_ and backup removed, topic post.txt has no product / cart; Drive skips "_" files
edit(d, lambda s: None)
demo.continue_layout(d)
script = json.loads((d / "script.json").read_text(encoding="utf-8"))
(d / "script.before-layout.json").write_text("{}", encoding="utf-8")
(d / "_mv_s1.mp3").write_bytes(b"x")
assert list(d.glob("_bo_*"))
demo.approve(d)
post = (d / "post.txt").read_text(encoding="utf-8")
assert "SẢN PHẨM" not in post and "Sản phẩm" not in post and "giỏ" not in post.lower() and "CHỦ ĐỀ" in post
assert not list(d.glob("_bo_*")) and not (d / "script.before-layout.json").exists()
import drive_upload  # noqa: E402

sent = []
os.environ["DRIVE_FOLDER_ID"] = "root"
drive_upload._session = lambda: None
drive_upload._find_or_create_folder = lambda s, n, p: "f"
drive_upload._upload_file = lambda s, p, parent, existing_id=None: (sent.append(p.name), {"md5Checksum": md5(p)})[1]
(d / "_rename_plan.json").write_text("{}")
(d / "script.before-layout.json").write_text("{}")
drive_upload.upload_video_folder(d, "x")
assert sent and not [n for n in sent if n.startswith("_") or n == "script.before-layout.json"], sent
assert "script.json" in sent and "post.txt" in sent
os.environ["DRIVE_FOLDER_ID"] = ""
print("10 approve / drive OK")

# ---- 11. product gate: no TTS, sids + brief, then cta rules
product = {"name": "Máy hút bụi", "price": 189000, "category": "Nhà cửa", "images": [], "selling_points": ["Nhẹ"],
           "product_url": "", "notes": "", "style": None, "sheet_row": None, "voice": "edge"}
demo.generate_script = lambda p, st: {"hook": "H", "caption": "c", "hashtags": [], "style": "simple", "segments": [
    {"kind": "product", "speaker": "narrator", "line": "Một", "text": "", "brief": "ý 1"},
    {"kind": "product", "speaker": "narrator", "line": "Hai", "text": "", "brief": "ý 2"},
    {"kind": "cta", "speaker": "narrator", "line": "Mua", "text": "", "brief": "mua"}], **({})}
n0 = len(tts_calls)
orig_assign = demo.assign_sids
real_gs = demo.generate_script


def gs(p, st):
    s = real_gs(p, st)
    orig_assign(s)
    return s


demo.generate_script = gs
r = demo.run_one(product, base, "simple", False, gate=True)
p = Path(r["dir"])
sc = json.loads((p / "script.json").read_text(encoding="utf-8"))
assert sc["stage"] == "script_review" and len(tts_calls) == n0 and not list(p.glob("audio_*"))
assert demo.SHEET_STATUS["script_review"] == "script_review"
demo.continue_layout(p)
invariant(p)
assert len(tts_calls) == n0 + 3
print("11 product gate OK")

# ---- 12. real render of a topic with no image (plain background), real FFmpeg, fake voice
demo.render_video = real_render
r = demo.run_topic({"name": "Thử nền trơn", "outline": "Mở đầu\nÝ giữa\nKết"}, base)
out = Path(r["dir"])
demo.continue_layout(out)
assert (out / "video.mp4").stat().st_size > 1000
print("12 real render OK")
shutil.rmtree(T, ignore_errors=True)
print("ALL OK")
