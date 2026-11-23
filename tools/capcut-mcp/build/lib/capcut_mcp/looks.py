"""Context-aware visual looks (DR-0013 Q-1): pick transitions, image motion, clip/text animations,
filters and scene effects from the product category and the scene's role, instead of plain stills.

A spec may set "look": "auto" (default: detect from category / product_name), a look name
("food", "beauty", "fashion", "tea", "tech", "home"), or "none". Values already set on a scene
always win, so Claude can override any single effect per scene.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

ROLES = ("hook", "point", "price", "story", "cta")

# Keywords are matched without diacritics, whole words. First match wins, in this order.
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("tea", ["tra", "am tra", "tra xanh", "tra o long", "tra dao", "ca phe", "cafe"]),
    ("food", ["nau an", "do an", "an vat", "banh", "thuc pham", "bep", "nha bep", "gia vi", "do uong",
              "snack", "mon an", "noi chien", "bot"]),
    ("beauty", ["lam dep", "my pham", "duong da", "trang diem", "son", "kem chong nang", "serum",
                "nuoc hoa", "cham soc da", "toc"]),
    ("fashion", ["thoi trang", "quan ao", "ao", "vay", "dam", "giay", "dep", "tui xach", "trang suc",
                 "phu kien thoi trang", "dong ho"]),
    ("tech", ["dien tu", "cong nghe", "dien thoai", "tai nghe", "loa", "may tinh", "laptop", "sac",
              "camera", "thiet bi", "phu kien dien thoai", "smart"]),
    ("home", ["nha cua", "gia dung", "do gia dung", "doi song", "noi that", "ve sinh"]),
]

# Per look: defaults for every scene, then per-role overrides. Names are pycapcut enum members
# (or capcut_builder ALIASES); unknown names are dropped at build time, never fatal.
LOOKS: dict[str, dict[str, Any]] = {
    "food": {
        "all": {"filter": "美食1", "filter_intensity": 60, "transition": "push_in"},
        "hook": {"motion": "zoom_in", "clip_in": "dynamic_zoom", "scene_effect": "细闪", "text_in": "bounce"},
        "point": {"motion": ["pan_left", "zoom_in", "pan_right"], "text_in": "pop",
                  "transition": ["push_in", "slide_left", "flash_white"]},
        "price": {"motion": "zoom_in", "scene_effect": "金粉闪闪", "text_in": "zoom", "text_loop": "pulse"},
        "story": {"motion": "zoom_out", "text_in": "fade", "transition": "dissolve"},
        "cta": {"motion": "zoom_out", "scene_effect": "五彩纸屑", "text_in": "pop", "text_loop": "pulse"},
    },
    "beauty": {
        "all": {"filter": "净透", "filter_intensity": 55, "transition": "dissolve"},
        "hook": {"motion": "zoom_in", "clip_in": "fade", "scene_effect": "仙尘闪闪", "text_in": "shine"},
        "point": {"motion": ["zoom_out", "pan_right", "zoom_in"], "text_in": "fade",
                  "transition": ["dissolve", "flash_white"]},
        "price": {"motion": "zoom_in", "scene_effect": "细闪", "text_in": "zoom", "text_loop": "float"},
        "story": {"motion": "zoom_out", "text_in": "fade"},
        "cta": {"motion": "zoom_out", "scene_effect": "柔光", "text_in": "pop", "text_loop": "pulse"},
    },
    "fashion": {
        "all": {"filter": "Soft_Grain", "filter_intensity": 50, "transition": "slide_left"},
        "hook": {"motion": "pan_right", "clip_in": "slide_left", "scene_effect": "闪光灯", "text_in": "punch"},
        "point": {"motion": ["pan_left", "pan_right", "zoom_in"], "text_in": "slide_left",
                  "transition": ["slide_left", "glitch", "move_right"]},
        "price": {"motion": "zoom_in", "scene_effect": "金粉闪闪", "text_in": "zoom", "text_loop": "pulse"},
        "story": {"motion": "zoom_out", "text_in": "fade"},
        "cta": {"motion": "zoom_out", "scene_effect": "胶片漏光", "text_in": "pop", "text_loop": "pulse"},
    },
    "tea": {
        "all": {"filter": "白茶", "filter_intensity": 60, "transition": "dissolve"},
        "hook": {"motion": "zoom_out", "clip_in": "fade", "scene_effect": "丁达尔光线", "text_in": "fade"},
        "point": {"motion": ["pan_right", "zoom_out", "pan_left"], "text_in": "fade"},
        "price": {"motion": "zoom_in", "scene_effect": "柔光", "text_in": "zoom"},
        "story": {"motion": "zoom_out", "text_in": "fade"},
        "cta": {"motion": "zoom_out", "scene_effect": "光晕", "text_in": "fade", "text_loop": "float"},
    },
    "tech": {
        "all": {"filter": "清晰冷调", "filter_intensity": 50, "transition": "glitch"},
        "hook": {"motion": "zoom_in", "clip_in": "dynamic_zoom", "scene_effect": "RGB_故障", "text_in": "glitch"},
        "point": {"motion": ["zoom_in", "pan_left", "pan_right"], "text_in": "typewriter",
                  "transition": ["glitch", "push_in", "slide_up"]},
        "price": {"motion": "zoom_in", "scene_effect": "动感光束", "text_in": "zoom", "text_loop": "pulse"},
        "story": {"motion": "zoom_out", "text_in": "fade"},
        "cta": {"motion": "zoom_out", "scene_effect": "光晕", "text_in": "pop", "text_loop": "pulse"},
    },
    "home": {
        "all": {"filter": "清晰", "filter_intensity": 50, "transition": "dissolve"},
        "hook": {"motion": "zoom_in", "clip_in": "zoom", "text_in": "pop"},
        "point": {"motion": ["zoom_in", "pan_right", "zoom_out"], "text_in": "slide_up",
                  "transition": ["dissolve", "slide_up", "push_in"]},
        "price": {"motion": "zoom_in", "scene_effect": "细闪", "text_in": "zoom", "text_loop": "pulse"},
        "story": {"motion": "zoom_out", "text_in": "fade"},
        "cta": {"motion": "zoom_out", "text_in": "pop", "text_loop": "pulse"},
    },
}

SCENE_KEYS = ("motion", "transition", "clip_in", "filter", "filter_intensity", "scene_effect")
TEXT_KEYS = ("text_in", "text_loop")


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def detect_look(category: str = "", product_name: str = "") -> str:
    for field in (category, product_name):
        text = _plain(field)
        for look, words in CATEGORY_KEYWORDS:
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words):
                return look
    return "home"


def _pick(value: Any, n: int) -> Any:
    return value[n % len(value)] if isinstance(value, list) else value


def apply_look(spec: dict[str, Any]) -> dict[str, Any]:
    """Fill missing effect fields on every scene from the chosen look. Returns the spec (mutated copy)."""
    look_name = (spec.get("look") or "auto").strip().lower()
    if look_name == "none":
        return spec
    if look_name == "auto":
        look_name = detect_look(spec.get("category", ""), spec.get("product_name", "") or spec.get("name", ""))
    look = LOOKS.get(look_name, LOOKS["home"])
    spec["look_used"] = look_name
    counters: dict[str, int] = {}
    scenes = spec.get("scenes") or []
    for i, sc in enumerate(scenes):
        role = sc.get("role") or ("hook" if i == 0 else "cta" if i == len(scenes) - 1 else "point")
        n = counters.get(role, 0)
        counters[role] = n + 1
        merged = {**look.get("all", {}), **look.get(role, {})}
        for key in SCENE_KEYS:
            if key in merged and sc.get(key) in (None, ""):
                sc[key] = _pick(merged[key], n)
        for t in sc.get("texts") or []:
            if not isinstance(t, dict):
                continue
            for key in TEXT_KEYS:
                if key in merged and key not in t:
                    # Only the main line of a scene gets a loop animation; small print stays calm.
                    if key == "text_loop" and float(t.get("size", 9)) < 9:
                        continue
                    t[key] = _pick(merged[key], n)
    return spec
