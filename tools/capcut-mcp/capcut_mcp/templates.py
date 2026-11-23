"""Product-ad templates: product info -> video spec."""

from __future__ import annotations

import re
from typing import Any

STYLES: dict[str, dict[str, Any]] = {
    "energetic": {  # TikTok Shop / Reels: nhanh, nhiều chuyển cảnh mạnh
        "transitions": ["flash_white", "push_in", "slide_left", "glitch"],
        "motions": ["zoom_in", "pan_left", "zoom_out", "pan_right"],
        "text_in": "pop", "title_in": "bounce", "price_loop": "pulse", "point_dur": 2.4,
        "theme": {"primary": "#FF2D55", "accent": "#FFD60A", "text": "#FFFFFF", "dark": "#111111"},
    },
    "elegant": {  # mỹ phẩm, thời trang, đồ cao cấp
        "transitions": ["dissolve"],
        "motions": ["zoom_out", "pan_right", "zoom_in"],
        "text_in": "fade", "title_in": "shine", "price_loop": None, "point_dur": 3.0,
        "theme": {"primary": "#1C1C1E", "accent": "#D4AF37", "text": "#FFFFFF", "dark": "#0B0B0C"},
    },
    "minimal": {  # đồ gia dụng, công nghệ: rõ ràng, sạch
        "transitions": ["dissolve", "slide_up"],
        "motions": ["zoom_in"],
        "text_in": "slide_up", "title_in": "fade", "price_loop": None, "point_dur": 2.8,
        "theme": {"primary": "#0A84FF", "accent": "#30D158", "text": "#FFFFFF", "dark": "#101418"},
    },
}


def fmt_price(v: Any, currency: str = "đ") -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)):
        return f"{int(v):,}".replace(",", ".") + currency
    return str(v)


def _num(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        digits = re.sub(r"[^\d]", "", v)
        return float(digits) if digits else None
    return None


def product_spec(
    *, product_name: str, images: list[str], selling_points: list[str],
    price: Any = None, old_price: Any = None, hook: str | None = None,
    cta: str | None = None, voucher: str | None = None, platform: str = "TikTok Shop",
    style: str = "energetic", aspect: str = "9:16", music: str | None = None,
    voiceover: str | None = None, theme: dict[str, str] | None = None,
    font: str | None = None, draft_name: str | None = None,
    category: str = "", look: str = "auto", narrations: list[str] | None = None,
) -> dict[str, Any]:
    if not images:
        raise ValueError("Cần ít nhất 1 ảnh/video sản phẩm")
    st = STYLES.get(style)
    if st is None:
        raise ValueError(f"style phải là một trong {list(STYLES)}")
    th = dict(st["theme"])
    th.update(theme or {})
    tr, mo = st["transitions"], st["motions"]
    img = lambda i: images[i % len(images)]  # noqa: E731
    f = {"font": font} if font else {}

    scenes: list[dict[str, Any]] = []
    # 1. Hook
    scenes.append({
        "media": img(0), "duration": 2.6, "motion": "zoom_in", "transition": tr[0],
        "texts": [
            {"text": hook or f"Đừng mua {product_name} khi chưa xem video này!", "position": "top",
             "size": 11, "color": th["text"], "bg": th["primary"], "text_in": st["title_in"], **f},
            {"text": product_name, "position": "bottom", "size": 9, "color": th["accent"],
             "border": "#000000", "text_in": st["text_in"], "start": 0.4, **f},
        ],
    })
    # 2. Selling points
    for i, point in enumerate(selling_points[:6]):
        scenes.append({
            "media": img(i + 1), "duration": st["point_dur"], "motion": mo[i % len(mo)],
            "transition": tr[(i + 1) % len(tr)],
            "texts": [{"text": f"{i + 1}. {point}", "position": "bottom", "size": 9.5,
                       "color": th["text"], "bg": th["primary"], "text_in": st["text_in"], **f}],
        })
    # 3. Price / offer
    if price not in (None, ""):
        texts = [{"text": f"Giá chỉ {fmt_price(price)}", "position": "center", "size": 13,
                  "color": th["accent"], "border": "#000000", "text_in": "zoom",
                  "text_loop": st["price_loop"], **f}]
        p, o = _num(price), _num(old_price)
        if o and p and o > p:
            texts.append({"text": f"Giá gốc {fmt_price(old_price)}", "position": "lower", "size": 7.5,
                          "color": "#DDDDDD", "start": 0.3, **f})
            texts.append({"text": f"GIẢM {round((1 - p / o) * 100)}%", "position": "top", "size": 11,
                          "color": th["text"], "bg": th["primary"], "text_in": "pop", **f})
        scenes.append({"media": img(len(selling_points) + 1), "duration": 3.0, "motion": "zoom_in",
                       "transition": tr[0], "texts": texts})
    # 4. CTA
    cta_texts = [{"text": cta or f"Bấm vào giỏ hàng {platform} để mua ngay!", "position": "center",
                  "size": 10.5, "color": th["text"], "bg": th["primary"], "text_in": "pop",
                  "text_loop": "pulse" if style == "energetic" else None, **f}]
    if voucher:
        cta_texts.append({"text": f"Nhập mã {voucher} để được giảm thêm", "position": "lower",
                          "size": 8, "color": th["accent"], "start": 0.4, **f})
    scenes.append({"media": img(0), "duration": 3.2, "motion": "zoom_out", "texts": cta_texts})

    roles = ["hook"] + ["point"] * len(selling_points[:6]) + (["price"] if price not in (None, "") else []) + ["cta"]
    for sc, role in zip(scenes, roles):
        sc["role"] = role
    # Narration lines in scene order (hook, points..., price, cta). A scene without a line stays silent.
    for sc, line in zip(scenes, narrations or []):
        if (line or "").strip():
            sc["narration"] = line.strip()

    spec: dict[str, Any] = {"name": draft_name or f"QC - {product_name}", "aspect": aspect,
                            "theme": th, "scenes": scenes, "category": category,
                            "product_name": product_name, "look": look}
    if music:
        spec["music"] = {"path": music, "volume": 0.35 if voiceover else 0.6}
    if voiceover:
        spec["voiceover"] = {"path": voiceover, "volume": 1.0}
    return spec


def caption(product_name: str, selling_points: list[str], price: Any, link: str | None,
            platform: str, voucher: str | None) -> str:
    tags = " ".join("#" + re.sub(r"\W", "", w) for w in product_name.split()[:3] if re.sub(r"\W", "", w))
    lines = [f"🔥 {product_name}"] + [f"✅ {p}" for p in selling_points[:5]]
    if price not in (None, ""):
        lines.append(f"💰 Giá chỉ {fmt_price(price)}")
    if voucher:
        lines.append(f"🎁 Mã giảm: {voucher}")
    if link:
        lines.append(f"👉 Mua tại: {link}")
    lines.append(f"{tags} #{platform.replace(' ', '')} #review #xuhuong")
    return "\n".join(lines)
