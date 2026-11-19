"""
Transcribe each voice clip with Groq Whisper and compare it with the script (DR-0004, skill
audio-check step 3). Catches Gemini TTS reading words that are not in the line (2026-11-13: the
oolong tea video, scene 2 added "... bán có 120 ngàn một túi").

  PY=$(git rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python
  $PY scripts/transcript_check.py storage/videos/<folder>               # every audio_N.mp3
  $PY scripts/transcript_check.py storage/videos/<folder> --scenes 2    # only scene 2 (audio_1.mp3)

For each selected scene N (1-based, audio_{N-1}.mp3): one POST to
https://api.groq.com/openai/v1/audio/transcriptions (model whisper-large-v3, language vi,
temperature 0). The transcript is compared with `audio_line` (else `line`) after normalising both:
lower case, accents removed (NFD, đ -> d), "%" -> "phần trăm" (one token, never a number),
punctuation removed, numbers turned into one token with
their value ("189.000đ", "189 nghìn", "một trăm tám mươi chín nghìn" -> #189000; "120k" -> #120000),
"đ"/"đồng"/"vnd" after a number -> "dong". Whisper accent mistakes ("đọng" -> "động") are not
differences, and a price read out in words is not a difference either.
Flags per scene (difflib alignment of the two token lists):
  "Nghi đọc bịa"   a run of >= --extra-words (default 4) consecutive transcript words not in the line,
                   or a number in the transcript (digits, or trăm/ngàn/nghìn/triệu/k) whose value
                   is not in the line
  "Nghi đọc thiếu" a run of >= --missing-words (default 4) consecutive line words not in the transcript
Results are signals for a human listener, never a pass of the audio (C-0004-3; Whisper also
mishears and can hallucinate on silence, R-4).

Key: GROQ_API_KEY from the environment; if the variable is not set at all, from .env of this
checkout, else .env of the main repo (git common dir). An empty GROQ_API_KEY= in the environment is
used as is (empty -> error), so tests can switch the key off. The key is never printed.
No new environment variable (DR-0004). Model can be changed with --model.

Groq free plan limits, from the official docs (fetched 2026-11-16):
  console.groq.com/docs/rate-limits, "Free Plan Limits", whisper-large-v3 (and -turbo):
    20 requests/minute, 2,000 requests/day, 7,200 audio seconds/hour, 28,800 audio seconds/day.
  console.groq.com/docs/speech-to-text: max file 25 MB on the free tier; every request is billed as
    at least 10 seconds of audio, so a 3 s clip counts as 10 s -> about 720 clips/hour, 2,880/day.
  Checked live on 2026-11-16: the response header x-ratelimit-limit-requests was 2000 (per day).
  Limits are per model and per organisation: Whisper does not use the chat model's quota
  (qwen/qwen3.8-27b, script writing), but shares it with any other Whisper use of the same account.
This script waits --interval seconds (default 3.5, i.e. under 20/minute) between calls and stores
the x-ratelimit-* response headers of the last call in transcript.json to confirm the real limits.

Vietnamese only: a travel folder (topic.json, English voice) is refused before any Groq call, since
the language sent to Whisper is fixed to "vi" and the comparison rules are Vietnamese.
HTTP 429 and 5xx are retried once after retry-after (default 2 s; not retried when the server asks
for more than 20 s). Every request, retries included, is counted in groq_calls.

Writes <out-dir>/transcript.json, only when every selected scene was transcribed; on any error a
stale transcript.json from an earlier run is removed so it cannot be read as the current result.
Default out-dir: storage/review-frames/<folder>/ of this checkout when the folder is
<repo>/storage/videos/<folder>; storage/review-frames/<folder>__sandbox/ for a copy elsewhere (e.g.
sandbox_render.py --keep), with "sandbox": true in the JSON. The video folder is only read, and an
--out-dir inside it or inside any storage/videos/ is refused (C-0004-5).

Exit codes: 0 = transcribed (flags are in the output); 1 = error (no key, invalid key, HTTP 429 or
5xx after the retry, network, missing audio file, travel folder, bad --out-dir, bad args).
"""
import argparse
import difflib
import http.client
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-large-v3"
TIMEOUT_S = 60
RETRY_MAX_WAIT_S = 20    # one retry for HTTP 429 / 5xx when retry-after is at most this
RETRY_DEFAULT_WAIT_S = 2
BAD_EXTRA, BAD_MISSING, BAD_NUMBER = "Nghi đọc bịa", "Nghi đọc thiếu", "Số lạ"


class CheckError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Text normalisation and comparison (no network; D-10 calls these directly)
# ---------------------------------------------------------------------------

DIGIT_WORDS = {"khong": 0, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4, "nam": 5, "lam": 5,
               "sau": 6, "bay": 7, "tam": 8, "chin": 9}
SCALE_WORDS = {"nghin": 1000, "ngan": 1000, "trieu": 1_000_000}   # "tỷ" left out: "một tý" = "a bit"
NUMBER_WORDS = set(DIGIT_WORDS) | set(SCALE_WORDS) | {"muoi", "tram", "linh", "le"}
CURRENCY = {"d", "dong", "vnd"}


def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def raw_tokens(text: str) -> list:
    t = strip_accents(text.replace("%", " phần trăm ")).lower()   # "50%" is read "năm mươi phần trăm"
    t = re.sub(r"(?<=\d)[.,](?=\d{3}(?!\d))", "", t)        # 189.000 / 1,200,000 -> 189000 / 1200000
    t = re.sub(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)", " ", t)  # 189000d -> 189000 d, 120k -> 120 k
    return re.findall(r"[a-z0-9]+", t)


def _is_digit(w: str) -> bool:
    return w.isdigit() or w in DIGIT_WORDS


def _words_value(words: list) -> int:
    """Value of a Vietnamese number in words/digits ('mot tram hai muoi nghin' -> 120000)."""
    total, group, last = 0, 0, None
    for w in words:
        if w.isdigit():
            last = int(w)
        elif w in DIGIT_WORDS:
            last = DIGIT_WORDS[w]
        elif w == "muoi":
            group += (last if last is not None else 1) * 10
            last = None
        elif w == "tram":
            group += (last if last is not None else 1) * 100
            last = None
        elif w in ("linh", "le"):
            continue
        elif w in SCALE_WORDS or w == "k":
            total += (group + (last or 0) or 1) * (1000 if w == "k" else SCALE_WORDS[w])
            group, last = 0, None
    return total + group + (last or 0)


def scan(text: str) -> list:
    """Normalised tokens as (token, strong). A number becomes '#<value>': digits, digits with a scale
    word, or number words with a scale word are strong (they can be flagged); a lone digit word
    ("tám", "năm", "sau") is a weak '#<value>' so it still matches "8", but is never flagged because
    the same spelling is also an ordinary word (năm = five / year, sau = six / after)."""
    raw, out, i = raw_tokens(text), [], 0
    while i < len(raw):
        j = i
        while j < len(raw) and (raw[j].isdigit() or raw[j] in NUMBER_WORDS
                                or (raw[j] == "k" and j > i and raw[j - 1].isdigit())):
            j += 1
        span = raw[i:j]
        for p in range(1, len(span)):
            # two digits in a row ("hai ba", "2 3") are two things, not one number
            if _is_digit(span[p]) and _is_digit(span[p - 1]):
                span = span[:p]
                break
            # a digit word right after trăm or a scale word continues the number only when a
            # mươi/trăm/scale word follows ("một trăm tám mươi", "một triệu hai trăm"); otherwise it
            # starts the next phrase: "tám trăm | năm" (800 years), "120 ngàn | một túi"
            nxt = span[p + 1] if p + 1 < len(span) else None
            if (span[p] in DIGIT_WORDS and (span[p - 1] in SCALE_WORDS or span[p - 1] in ("k", "tram"))
                    and not (nxt in ("muoi", "tram") or nxt in SCALE_WORDS)):
                span = span[:p]
                break
        # filler words at the end ("le" = "lẻ"/"lễ", "linh") that are not part of a number
        while span and span[-1] in ("linh", "le"):
            span = span[:-1]
        has_digit = any(w.isdigit() for w in span)
        has_scale = any(w in SCALE_WORDS or w in ("muoi", "tram", "k") for w in span)
        has_digit_word = any(w in DIGIT_WORDS for w in span)
        strong = bool(span) and (has_digit or (has_scale and has_digit_word) or span == ["muoi"])
        if strong or (len(span) == 1 and span[0] in DIGIT_WORDS):
            out.append((f"#{_words_value(span)}", strong, " ".join(span)))
            i += len(span)
            if strong and i < len(raw) and raw[i] in CURRENCY:
                out.append(("dong", False, raw[i]))
                i += 1
            continue
        if raw[i] == "phan" and i + 1 < len(raw) and raw[i + 1] == "tram":
            out.append(("phan_tram", False, "phan tram"))   # "phần trăm" = percent, not the number 100
            i += 2
            continue
        out.append((raw[i], raw[i] in SCALE_WORDS or raw[i] == "tram", raw[i]))  # bare "nghìn", "trăm"
        i += 1
    return out


def tokens(text: str) -> list:
    return [t for t, *_ in scan(text)]


def compare(reference: str, heard: str, extra_words: int = 4, missing_words: int = 4) -> dict:
    """Align line vs transcript. Returns extra / missing runs (as the normalised words that were
    read / written, without accents) and unexpected numbers (values)."""
    ref_scan, heard_scan = scan(reference), scan(heard)
    ref, hyp = [t for t, *_ in ref_scan], [t for t, *_ in heard_scan]
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    extra, missing = [], []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op in ("insert", "replace") and b1 - b0 >= extra_words:
            extra.append(" ".join(w for *_, w in heard_scan[b0:b1]))
        if op in ("delete", "replace") and a1 - a0 >= missing_words:
            missing.append(" ".join(w for *_, w in ref_scan[a0:a1]))
    ref_set = set(ref)
    # "#120000" -> "120000"; a bare scale word ("trieu") is shown as is
    numbers = sorted({t.lstrip("#") for t, strong, _ in heard_scan if strong and t not in ref_set})
    flags = ([BAD_EXTRA] if extra or numbers else []) + ([BAD_MISSING] if missing else [])
    return {"extra": extra, "missing": missing, "unexpected_numbers": numbers, "flags": flags,
            "similarity": round(sm.ratio(), 3)}


# ---------------------------------------------------------------------------
# Groq call
# ---------------------------------------------------------------------------

def _read_env_file(path: Path, key: str):
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def groq_key() -> str:
    if "GROQ_API_KEY" in os.environ:          # set, even empty: the caller decides (tests use GROQ_API_KEY=)
        return os.environ["GROQ_API_KEY"].strip()
    roots = [CODE_ROOT]
    try:
        common = subprocess.run(["git", "-C", str(CODE_ROOT), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True, timeout=10).stdout.strip()
        if common:
            roots.append(Path(common).parent)
    except (OSError, subprocess.SubprocessError):
        pass
    for root in roots:
        value = _read_env_file(root / ".env", "GROQ_API_KEY")
        if value:
            return value
    return ""


def _multipart(fields: dict, file_field: str, path: Path) -> tuple:
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
                 f'filename="{path.name}"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode())
    parts.append(path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _retry_wait(headers) -> float:
    """Seconds asked by retry-after (default RETRY_DEFAULT_WAIT_S), or None if more than RETRY_MAX_WAIT_S."""
    raw = (headers.get("retry-after") if headers else None) or ""
    try:
        wait = float(raw)
    except ValueError:
        wait = RETRY_DEFAULT_WAIT_S
    return max(wait, 0.0) if wait <= RETRY_MAX_WAIT_S else None


def transcribe(path: Path, key: str, model: str, stats: dict) -> tuple:
    """(text, x-ratelimit headers). One retry for HTTP 429 / 5xx. stats["requests"] counts every POST.
    Raises CheckError with a message that never contains the key."""
    body, ctype = _multipart({"model": model, "language": "vi", "temperature": "0",
                              "response_format": "json"}, "file", path)

    def clean(s: str) -> str:
        return s.replace(key, "***") if key else s

    for attempt in (1, 2):
        req = urllib.request.Request(API_URL, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": ctype,
                                              "User-Agent": "transcript-check/1.0"})
        stats["requests"] = stats.get("requests", 0) + 1
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                data = json.load(resp)
                limits = {k.lower(): v for k, v in resp.headers.items() if k.lower().startswith("x-ratelimit")}
            return (data.get("text") or "").strip(), limits
        except urllib.error.HTTPError as e:
            detail = clean(e.read().decode("utf-8", "replace"))[:200]
            if e.code == 401:
                raise CheckError("Groq rejected GROQ_API_KEY (HTTP 401): check the key in .env") from None
            if e.code == 429 or e.code >= 500:
                wait = _retry_wait(e.headers)
                if attempt == 1 and wait is not None:
                    print(f"  Groq HTTP {e.code}, retrying once in {wait:g} s", file=sys.stderr, flush=True)
                    time.sleep(wait)
                    continue
            if e.code == 429:
                wait = e.headers.get("retry-after", "?") if e.headers else "?"
                raise CheckError(f"Groq rate limit reached (HTTP 429, retry after {wait} s). Free plan for "
                                 f"{model}: 20 requests/min, 2,000/day, 28,800 audio s/day: {detail}") from None
            raise CheckError(f"Groq HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            raise CheckError(f"Network error calling Groq: {clean(str(e.reason))}") from None
        except (TimeoutError, OSError, http.client.HTTPException) as e:
            raise CheckError(f"Network error calling Groq ({type(e).__name__}): {clean(str(e))}") from None
        except json.JSONDecodeError:
            raise CheckError("Groq answered with something that is not JSON") from None
    raise CheckError("Groq request failed after one retry")  # not reached: the loop returns or raises


# ---------------------------------------------------------------------------
# Output folder (C-0004-5: never write into a video folder or any storage/videos/)
# ---------------------------------------------------------------------------

def _repo_roots() -> list:
    """This checkout and the main repo (git common dir), whose storage/videos/ hold the real videos."""
    roots = [CODE_ROOT]
    try:
        common = subprocess.run(["git", "-C", str(CODE_ROOT), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True, timeout=10).stdout.strip()
        if common and Path(common).parent.resolve() not in roots:
            roots.append(Path(common).parent.resolve())
    except (OSError, subprocess.SubprocessError):
        pass
    return roots


def is_real_folder(folder: Path) -> bool:
    """True when folder is <repo>/storage/videos/<name> of this checkout or the main repo; False for a
    copy anywhere else (e.g. the temp dir of sandbox_render.py --keep)."""
    return folder.parent in [(r / "storage" / "videos").resolve() for r in _repo_roots()]


def _in_videos_tree(path: Path) -> bool:
    parts = path.parts
    return any(parts[k] == "storage" and parts[k + 1] == "videos" for k in range(len(parts) - 1))


def output_dir(folder: Path, out_dir_arg) -> tuple:
    """(out_dir, sandbox). Default storage/review-frames/<name>/ of this checkout for a real folder,
    storage/review-frames/<name>__sandbox/ for a copy, so the result of a copy never overwrites (or
    is read as) the result of the real video. --out-dir inside the video folder or inside any
    storage/videos/ is refused."""
    sandbox = not is_real_folder(folder)
    if out_dir_arg:
        out = Path(out_dir_arg).expanduser().resolve()
        if out == folder or folder in out.parents or _in_videos_tree(out):
            raise CheckError(f"--out-dir {out} is inside the video folder or a storage/videos/ tree; "
                        f"results must not be written next to videos (C-0004-5)")
        return out, sandbox
    name = folder.name + ("__sandbox" if sandbox else "")
    return CODE_ROOT / "storage" / "review-frames" / name, sandbox


def parse_scenes(text: str, n: int) -> list:
    if not text:
        return list(range(n))
    picked = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit() or not 1 <= int(part) <= n:
            raise CheckError(f"--scenes: '{part}' is not a scene number 1..{n}")
        picked.append(int(part) - 1)
    return sorted(set(picked))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Transcribe audio_N.mp3 with Groq Whisper and flag words read but not in the line "
                    "(Nghi đọc bịa), words of the line not read (Nghi đọc thiếu) and unexpected numbers. "
                    "Writes transcript.json; only reads the video folder. One Groq request per scene.")
    ap.add_argument("folder", help="video folder, e.g. storage/videos/<folder>")
    ap.add_argument("--scenes", default="", help="only these scenes, 1-based, comma-separated (e.g. 1,2)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Groq transcription model (default {DEFAULT_MODEL})")
    ap.add_argument("--extra-words", type=int, default=4,
                    help="flag a run of at least this many transcript words not in the line (default 4)")
    ap.add_argument("--missing-words", type=int, default=4,
                    help="flag a run of at least this many line words not heard (default 4)")
    ap.add_argument("--interval", type=float, default=3.5,
                    help="seconds between Groq calls (default 3.5; free plan allows 20/min)")
    ap.add_argument("--out-dir", help="where to write transcript.json (default storage/review-frames/<folder>/, "
                                      "or <folder>__sandbox/ for a copy outside storage/videos/; never inside "
                                      "a storage/videos/ tree)")
    args = ap.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    try:
        out_dir, sandbox = output_dir(folder, args.out_dir)
    except CheckError as e:
        print(f"transcript_check: error: {e} (Groq calls made: 0)", file=sys.stderr)
        return 1
    dest = out_dir / "transcript.json"
    stats, rows, limits = {"requests": 0}, [], {}
    try:
        if (folder / "topic.json").is_file():
            raise CheckError(f"{folder.name} is a travel folder (topic.json): transcript_check only handles "
                             f"Vietnamese voice (Whisper language is fixed to vi), English travel videos "
                             f"are not supported")
        if not (folder / "script.json").is_file():
            raise CheckError(f"No script.json in {folder}")
        segments = json.loads((folder / "script.json").read_text(encoding="utf-8")).get("segments") or []
        if not segments:
            raise CheckError("script.json has no segments")
        picked = parse_scenes(args.scenes, len(segments))
        for i in picked:
            if not (folder / f"audio_{i}.mp3").is_file():
                raise CheckError(f"No audio_{i}.mp3 (scene {i + 1}) in {folder}")
        key = groq_key()
        if not key:
            raise CheckError("GROQ_API_KEY is not set (environment or .env of the repo)")
        for n, i in enumerate(picked):
            if n:
                time.sleep(args.interval)
            seg = segments[i]
            path = folder / f"audio_{i}.mp3"
            print(f"Groq call {n + 1}/{len(picked)}: scene {i + 1} ({path.name})", file=sys.stderr, flush=True)
            heard, limits = transcribe(path, key, args.model, stats)
            reference = seg.get("audio_line") or seg.get("line") or ""
            rows.append({"scene": i + 1, "file": path.name, "line": reference, "transcript": heard,
                         **compare(reference, heard, args.extra_words, args.missing_words)})
    except (CheckError, json.JSONDecodeError) as e:
        if dest.is_file():
            dest.unlink()
            print(f"transcript_check: removed stale {dest}", file=sys.stderr)
        print(f"transcript_check: error: {e} (Groq calls made: {stats['requests']})", file=sys.stderr)
        return 1
    calls = stats["requests"]

    out_dir.mkdir(parents=True, exist_ok=True)
    flagged = [r["scene"] for r in rows if r["flags"]]
    report = {"folder": str(folder), "sandbox": sandbox, "source": "copy" if sandbox else "storage/videos",
              "model": args.model, "groq_calls": calls,
              "extra_words": args.extra_words, "missing_words": args.missing_words,
              "flagged_scenes": flagged, "rows": rows, "ratelimit_headers": limits,
              "note": "Signal only (C-0004-3): flagged scenes need a human listen; Whisper can mishear."}
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in rows:
        print(f"\nScene {r['scene']} ({r['file']}): {', '.join(r['flags']) or 'OK'}  similarity {r['similarity']}")
        print(f"  line:  {r['line']}")
        print(f"  heard: {r['transcript']}")
        for s in r["extra"]:
            print(f"  + extra:   {s}")
        if r["unexpected_numbers"]:
            print(f"  + numbers: {' '.join(r['unexpected_numbers'])}")
        for s in r["missing"]:
            print(f"  - missing: {s}")
    print(f"\n{len(flagged)} flagged of {len(rows)}, Groq calls: {calls} -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
