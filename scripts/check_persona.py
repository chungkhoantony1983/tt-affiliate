"""Self-check for demo.choose_persona (issue #41). Run: python scripts/check_persona.py"""
import os
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demo  # noqa: E402

os.environ.pop("GEMINI_TTS_PERSONA", None)


def pick(notes, category="Nhà cửa"):
    return demo.choose_persona({"name": "Xà bông", "category": category, "notes": notes})


for notes in ("Giọng nam nhé.", "giọng đọc nam, tự hào", "Không nói quá. Giọng nam nhé",
              "không dùng giọng nữ, dùng giọng nam", "Giọng đọc: nam", "Giọng đọc phải là nam", "Giọng: nam",
unicodedata.normalize("NFD", "Giọng nam nhé")):
    assert pick(notes) == "nam_bac", notes
for notes in ("Giọng nữ nhé", "giọng đọc là nữ miền Nam"):
    assert pick(notes, "Điện tử") == "nu_nam", notes
# not a voice request: the product-type default stays
for notes in ("", None, "Không dùng hình ảnh nữ giới", "phù hợp người Việt Nam", "giọng miền Nam",
              "giọng Nam Bộ", "trông giống nam giới", "đừng dùng giọng nam", "giọng nam và giọng nữ",
              "giọng nam nữ đều được", "giọng nam hay nữ đều được", "giọng nữ hoặc nam", "giọng nam/nữ"):
    assert pick(notes) == "nu_nam", notes
    assert pick(notes, "Điện tử") == "nam_bac", notes

os.environ["GEMINI_TTS_PERSONA"] = "nu_nam"
assert pick("Giọng nam nhé") == "nu_nam"  # .env wins over notes
print("choose_persona: OK")
