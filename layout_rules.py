"""Layout rules for the "script_review" step (DR-0014 section 4.3). stdlib only.

One place for the rules that demo.py (--continue / --rewrite) and, later, api/studio.py (PUT layout) share.
Every check returns a list of error strings in Vietnamese (shown to the operator); [] means valid.
"""
import re

SID_RE = re.compile(r"^s[1-9]\d{0,3}$")                       # C-0014-12: the sid ends up in file names
MIN_SCENES, MAX_SCENES = 2, 12
MAX_LINE, MAX_TEXT, MAX_BRIEF = 300, 60, 200
OUTLINE_MIN, OUTLINE_MAX, OUTLINE_LINE_MAX = 2, 12, 200

# Leading "1." / "2)" / "-" / "Cảnh 3:" of an outline line
_BULLET_RE = re.compile(r"^\s*(?:(?:cảnh|canh)\s*\d+\s*[:.)\-]|\d+\s*[.)\-:]|[-*•])\s*", re.I)

LOCKED_LAST = {"product": "cta", "topic": "outro"}
BODY_KINDS = {"product": {"product", "story"}, "topic": {"topic"}}


def norm_line(text) -> str:
    """Spoken line as compared for "needs a new voice": runs of whitespace (incl. newlines) become one space.
    demo.py and api/studio.py must both use this one function."""
    return " ".join(str(text or "").split())


def valid_sid(sid) -> bool:
    return isinstance(sid, str) and bool(SID_RE.match(sid))


def clean_outline(value) -> list:
    """Outline text (or list of lines) -> non-empty lines without bullets or numbering."""
    lines = value.splitlines() if isinstance(value, str) else list(value or [])
    out = []
    for raw in lines:
        line = " ".join(_BULLET_RE.sub("", str(raw), count=1).split())
        if line:
            out.append(line)
    return out


def check_outline(lines: list) -> list:
    n = len(lines)
    if not OUTLINE_MIN <= n <= OUTLINE_MAX:
        return [f"Cần từ {OUTLINE_MIN} đến {OUTLINE_MAX} dòng. Bạn đang có {n}."]
    return [f"Dòng {i + 1} dài quá {OUTLINE_LINE_MAX} ký tự." for i, s in enumerate(lines)
            if len(s) > OUTLINE_LINE_MAX]


def check_sids(segments: list) -> list:
    errors, seen = [], set()
    for i, seg in enumerate(segments):
        sid = seg.get("sid")
        if not valid_sid(sid):
            errors.append(f"Cảnh {i + 1} có mã không hợp lệ.")
        elif sid in seen:
            errors.append(f"Cảnh {i + 1} trùng mã với cảnh khác.")
        seen.add(sid)
    return errors


def check_scene_text(line: str, text: str = "") -> list:
    """Limits for AI-written or hand-typed text of one scene (empty line allowed here)."""
    errors = []
    if len(" ".join((line or "").split())) > MAX_LINE:
        errors.append(f"Lời đọc dài quá {MAX_LINE} ký tự.")
    if len((text or "").strip()) > MAX_TEXT:
        errors.append(f"Chữ trên hình dài quá {MAX_TEXT} ký tự.")
    return errors


def check_layout(segments: list, kind: str = "product", style: str = "simple", price=None,
                 strict_lines: bool = False) -> list:
    """kind: "product" | "topic". strict_lines: every scene needs a spoken line (--continue)."""
    n = len(segments)
    if not MIN_SCENES <= n <= MAX_SCENES:
        return [f"Video cần từ {MIN_SCENES} đến {MAX_SCENES} cảnh, hiện có {n}."]
    errors = check_sids(segments)
    last = LOCKED_LAST[kind]
    body = set(BODY_KINDS[kind])
    if kind == "product" and style != "story":
        body.discard("story")
    for i, seg in enumerate(segments):
        k, num = seg.get("kind"), i + 1
        if i == n - 1:
            if k != last:
                errors.append("Video sản phẩm cần đúng 1 cảnh Kêu gọi mua ở cuối." if kind == "product"
                              else "Video chủ đề cần đúng 1 cảnh Kết ở cuối.")
        elif k not in body:
            errors.append(f"Cảnh {num} có loại không hợp lệ cho video này.")
        line = norm_line(seg.get("line"))
        if strict_lines and not line:
            errors.append(f"Cảnh {num} chưa có lời đọc.")
        errors += [f"Cảnh {num}: {e}" for e in check_scene_text(line, seg.get("text") or "")]
        if len(str(seg.get("brief") or "")) > MAX_BRIEF:
            errors.append(f"Cảnh {num}: ý cảnh dài quá {MAX_BRIEF} ký tự.")
    if kind == "product" and price is not None and price != 0 and price < 1000:   # C-0007-2
        errors.append("Giá chỉ nhận 0 (ẩn giá) hoặc từ 1.000đ trở lên.")
    return errors


def _selftest() -> None:
    def segs(kinds, **extra):
        return [dict(sid=f"s{i + 1}", kind=k, line="Lời đọc", text="", brief="", **extra)
                for i, k in enumerate(kinds)]

    assert clean_outline("1. A\n- B\n\nCảnh 3: C\n 4) D ") == ["A", "B", "C", "D"]
    assert clean_outline("Nâng 3 nhịp") == ["Nâng 3 nhịp"]
    assert norm_line("a \n b\t c ") == "a b c" and norm_line(None) == ""
    assert check_outline(["a"]) and not check_outline(["a", "b"]) and check_outline(["a"] * 13)
    assert check_outline(["a", "x" * 201])
    assert [valid_sid(s) for s in ("s1", "s9999", "s0", "S2", "s12345", "s2/a", "../../x", "", None)] == \
           [True, True, False, False, False, False, False, False, False]
    assert not check_layout(segs(["product", "product", "cta"]), "product", price=189000)
    assert check_layout(segs(["product", "cta", "product"]))                     # cta in the middle
    assert check_layout(segs(["product", "product"]))                            # no cta
    assert check_layout(segs(["story", "product", "cta"]))                       # story needs style=story
    assert not check_layout(segs(["story", "product", "cta"]), style="story")
    assert check_layout(segs(["product", "cta"]), price=500)                     # price rule
    assert not check_layout(segs(["product", "cta"]), price=0)
    assert not check_layout(segs(["topic", "topic", "outro"]), "topic")
    assert check_layout(segs(["topic", "cta"]), "topic")                         # cta not allowed
    assert check_layout(segs(["topic"]), "topic")                                # too few
    assert check_layout(segs(["topic"] * 12 + ["outro"]), "topic")               # too many
    dup = segs(["topic", "outro"]); dup[1]["sid"] = "s1"
    assert check_layout(dup, "topic")                                            # duplicate sid
    empty = segs(["topic", "outro"]); empty[0]["line"] = " "
    assert not check_layout(empty, "topic") and check_layout(empty, "topic", strict_lines=True)
    long_line = segs(["topic", "outro"]); long_line[0]["line"] = "x" * 301
    assert check_layout(long_line, "topic")
    print("layout_rules selftest OK")


if __name__ == "__main__":
    _selftest()
