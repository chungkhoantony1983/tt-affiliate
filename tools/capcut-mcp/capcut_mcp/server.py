"""MCP server: lets Claude create CapCut promo videos for affiliate products."""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from . import common
from .templates import STYLES, caption, product_spec

mcp = FastMCP(
    "capcut",
    instructions=(
        "Tạo video quảng cáo sản phẩm (affiliate) dưới dạng dự án nháp CapCut và/hoặc file MP4. "
        "Quy trình gợi ý: gọi capcut_status trước; với sản phẩm mới dùng create_product_video; "
        "muốn tuỳ biến từng cảnh thì sửa 'spec' trả về rồi gọi build_video. "
        "Sau khi tạo draft, người dùng mở CapCut (có thể cần khởi động lại CapCut) để xem và xuất video."
    ),
)

Output = Literal["capcut", "mp4", "both"]


def _build(spec: dict[str, Any], output: Output) -> dict[str, Any]:
    result: dict[str, Any] = {}
    errors: dict[str, str] = {}
    if output in ("capcut", "both"):
        try:
            from .capcut_builder import build_capcut_draft
            result["capcut"] = build_capcut_draft(spec)
        except Exception as e:  # keep going so the MP4 can still be made
            errors["capcut"] = f"{type(e).__name__}: {e}"
    if output in ("mp4", "both"):
        try:
            from .ffmpeg_render import render_mp4
            result["mp4"] = render_mp4(spec)
        except Exception as e:
            errors["mp4"] = f"{type(e).__name__}: {e}"
    if errors:
        result["errors"] = errors
    return result


@mcp.tool()
def capcut_status() -> dict[str, Any]:
    """Kiểm tra môi trường: thư mục draft CapCut, ffmpeg, font, danh sách style."""
    folder = common.get_drafts_folder()
    try:
        import pycapcut  # noqa: F401
        pyc = True
    except Exception:
        pyc = False
    return {
        "os": platform.system(),
        "drafts_folder": str(folder) if folder else None,
        "drafts_folder_candidates": [str(p) for p in common.candidate_draft_folders()],
        "pycapcut_installed": pyc,
        "ffmpeg": common.find_ffmpeg(),
        "font_for_mp4": common.find_font(),
        "mp4_output_dir": str(common.OUTPUT_DIR),
        "styles": list(STYLES),
        "aspects": list(common.ASPECTS),
    }


@mcp.tool()
def set_drafts_folder(path: str) -> dict[str, Any]:
    """Đặt thủ công thư mục chứa draft của CapCut (thư mục com.lveditor.draft)."""
    p = Path(path).expanduser()
    if not p.is_dir():
        raise ValueError(f"Thư mục không tồn tại: {p}")
    cfg = common.load_config()
    cfg["drafts_folder"] = str(p)
    common.save_config(cfg)
    return {"drafts_folder": str(p)}


@mcp.tool()
def list_drafts() -> list[str]:
    """Liệt kê các dự án nháp trong thư mục CapCut."""
    folder = common.get_drafts_folder()
    if not folder:
        return []
    return sorted(d.name for d in folder.iterdir() if (d / "draft_content.json").exists()
                  or (d / "draft_info.json").exists())


@mcp.tool()
def list_effects(kind: Literal["transition", "clip_in", "clip_out", "text_in", "text_out", "text_loop",
                               "font", "filter", "scene_effect"],
                 query: str = "", limit: int = 80) -> dict[str, Any]:
    """Tra tên hiệu ứng CapCut dùng trong spec (chuyển cảnh, animation chữ, font, filter...).
    Có alias tiếng Anh (vd 'dissolve', 'pop', 'pulse'); tên gốc phần lớn là tiếng Trung."""
    from .capcut_builder import list_effect_names
    return list_effect_names(kind, query, limit)


@mcp.tool()
def create_product_video(
    product_name: str,
    images: list[str],
    selling_points: list[str],
    price: str | int | None = None,
    old_price: str | int | None = None,
    affiliate_link: str | None = None,
    voucher: str | None = None,
    hook: str | None = None,
    cta: str | None = None,
    platform_name: str = "TikTok Shop",
    style: Literal["energetic", "elegant", "minimal"] = "energetic",
    aspect: Literal["9:16", "1:1", "4:5", "16:9"] = "9:16",
    music: str | None = None,
    voiceover: str | None = None,
    font: str | None = None,
    draft_name: str | None = None,
    category: str = "",
    look: str = "auto",
    narrations: list[str] | None = None,
    output: Output = "both",
) -> dict[str, Any]:
    """Tạo video quảng cáo sản phẩm từ thông tin sản phẩm.

    category: danh mục (nấu ăn, làm đẹp, thời trang, trà, điện tử, gia dụng...). Quyết định bộ hiệu ứng hình
    (filter, hiệu ứng cảnh, animation chữ) và giọng đọc (nữ: nấu ăn/làm đẹp/thời trang; nam: trà/điện tử).
    look: 'auto' (theo danh mục), food|beauty|fashion|tea|tech|home hoặc 'none'.
    narrations: lời đọc từng cảnh theo thứ tự hook, từng điểm nổi bật, giá, CTA; đọc bằng edge-tts miễn phí
    và cảnh tự dài ra theo lời đọc. Chỉ dùng thông tin có thật về sản phẩm, không bịa số liệu.

    images: đường dẫn file trên máy hoặc URL ảnh/video sản phẩm (nên 3-6 ảnh).
    selling_points: 3-5 điểm nổi bật ngắn (mỗi ý dưới ~40 ký tự).
    price/old_price: số (199000) hoặc chuỗi ("199K"). Có old_price thì tự hiện % giảm.
    hook: câu mở đầu 2 giây gây chú ý; cta: lời kêu gọi cuối video.
    music/voiceover: file mp3/wav/m4a (tuỳ chọn). font: tên FontType (vd 'Montserrat').
    output: 'capcut' (draft), 'mp4' (render ffmpeg) hoặc 'both'.
    Trả về spec (có thể sửa rồi gọi build_video), kết quả và caption gợi ý kèm link affiliate.
    """
    spec = product_spec(product_name=product_name, images=images, selling_points=selling_points,
                        price=price, old_price=old_price, hook=hook, cta=cta, voucher=voucher,
                        platform=platform_name, style=style, aspect=aspect, music=music,
                        voiceover=voiceover, font=font, draft_name=draft_name,
                        category=category, look=look, narrations=narrations)
    result = _build(spec, output)
    result["caption"] = caption(product_name, selling_points, price, affiliate_link, platform_name, voucher)
    result["spec"] = spec
    return result


@mcp.tool()
def build_video(spec: dict[str, Any] | str, output: Output = "both") -> dict[str, Any]:
    """Dựng video từ spec tuỳ biến (JSON). Cấu trúc:
    {"name": str, "aspect": "9:16", "fps": 30, "theme": {...},
     "music": {"path": str, "volume": 0.5}, "voiceover": {"path": str},
     "scenes": [{"media": path|url|null, "duration": 3, "motion": "zoom_in|zoom_out|pan_left|pan_right|none",
                 "transition": "dissolve", "clip_in": "fade", "filter": null, "background": "#111111",
                 "texts": [{"text": str, "position": "top|upper|center|lower|bottom", "y": -0.6,
                            "size": 9, "color": "#FFFFFF", "bg": "#FF2D55", "border": "#000000",
                            "bold": true, "font": null, "start": 0, "end": 3,
                            "text_in": "pop", "text_out": null, "text_loop": null}]}]}
    """
    if isinstance(spec, str):
        spec = json.loads(spec)
    return _build(spec, output)


@mcp.tool()
def open_capcut() -> str:
    """Mở (hoặc khởi động lại để nạp draft mới) ứng dụng CapCut trên máy."""
    system = platform.system()
    if system == "Darwin":
        import time
        subprocess.run(["osascript", "-e", 'quit app "CapCut"'], capture_output=True)
        for _ in range(60):  # `open` while CapCut is still quitting is a no-op
            if subprocess.run(["pgrep", "-f", "CapCut.app/Contents/MacOS/CapCut$"],
                              capture_output=True).returncode:
                break
            time.sleep(0.5)
        _drop_stale_index()
        p = subprocess.run(["open", "-a", "CapCut"], capture_output=True, text=True)
        return "Đã mở CapCut" if p.returncode == 0 else f"Không mở được CapCut: {p.stderr}"
    if system == "Windows":
        import os
        exe = Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut/Apps/CapCut.exe"
        if exe.exists():
            subprocess.Popen([str(exe)])
            return "Đã mở CapCut"
        return "Không tìm thấy CapCut.exe, hãy mở CapCut thủ công"
    return "Hệ điều hành không hỗ trợ mở CapCut tự động"


def _drop_stale_index() -> None:
    """CapCut caches each draft folder in root_meta_info.json and never re-reads a folder
    we rebuilt in place; drop entries whose draft_id no longer matches the folder so the
    next launch rescans them. Only safe while CapCut is closed (it rewrites the file on quit)."""
    folder = common.get_drafts_folder()
    idx = folder / "root_meta_info.json" if folder else None
    if not idx or not idx.exists():
        return
    data = json.loads(idx.read_text("utf-8"))
    keep = []
    for d in data.get("all_draft_store", []):
        meta = Path(d.get("draft_fold_path", "")) / "draft_meta_info.json"
        try:
            ok = json.loads(meta.read_text("utf-8")).get("draft_id") == d.get("draft_id")
        except (OSError, ValueError):
            ok = True  # unreadable: leave CapCut's entry alone
        if ok:
            keep.append(d)
    if len(keep) != len(data.get("all_draft_store", [])):
        data["all_draft_store"] = keep
        idx.write_text(json.dumps(data, ensure_ascii=False), "utf-8")


# --------------------------------------------------------------------------- Tt Affiliate (DR-0013)

def _affiliate_root() -> Path:
    import os
    raw = os.environ.get("TT_AFFILIATE_DIR", "").strip()
    if not raw:
        raise ValueError("Chưa đặt TT_AFFILIATE_DIR (thư mục dự án Tt Affiliate) trong cấu hình MCP")
    root = Path(raw).expanduser().resolve()
    if not (root / "demo.py").is_file():
        raise ValueError(f"{root} không phải thư mục Tt Affiliate (không thấy demo.py)")
    return root


def _affiliate_folder(name: str) -> Path:
    """C-0013-3: only direct children of <TT_AFFILIATE_DIR>/storage/videos, no path tricks."""
    if not name or "/" in name or "\\" in name or ".." in name or name.startswith("."):
        raise ValueError("Tên thư mục video không hợp lệ")
    videos = (_affiliate_root() / "storage" / "videos").resolve()
    folder = (videos / name).resolve()
    if folder.parent != videos or not folder.is_dir():
        raise ValueError(f"Không thấy video '{name}' trong storage/videos")
    return folder


@mcp.tool()
def affiliate_list_videos(limit: int = 20) -> list[dict[str, Any]]:
    """Liệt kê video sản phẩm đã tạo trong Tt Affiliate (mới nhất trước): tên, trạng thái, đã xuất CapCut chưa."""
    videos = _affiliate_root() / "storage" / "videos"
    out = []
    for d in sorted((p for p in videos.iterdir() if p.is_dir()), reverse=True)[:limit]:
        product = _read_json(d / "product.json")
        if not product:
            continue  # travel / exercise folders are not supported
        out.append({"folder": d.name, "product": product.get("name"), "price": product.get("price"),
                    "has_video": (d / "video.mp4").is_file(),
                    "approved": (d / "post.txt").is_file(),
                    "capcut": _read_json(d / "capcut.json") or None})
    return out


@mcp.tool()
def affiliate_export_to_capcut(folder: str) -> dict[str, Any]:
    """Xuất một video sản phẩm của Tt Affiliate sang dự án CapCut (giữ giọng đọc đã có, không gọi AI).
    `folder` là tên thư mục trong storage/videos (lấy từ affiliate_list_videos)."""
    import subprocess
    import sys
    root = _affiliate_root()
    path = _affiliate_folder(folder)
    py = root / ".venv" / "bin" / "python"
    p = subprocess.run([str(py if py.exists() else sys.executable), str(root / "demo.py"), "--capcut", str(path)],
                       cwd=str(root), capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError((p.stdout + p.stderr).strip()[-1500:] or f"demo.py thoát mã {p.returncode}")
    return json.loads(p.stdout.strip().splitlines()[-1])


@mcp.tool()
def affiliate_fetch_product(url: str) -> dict[str, Any]:
    """Đọc trang sản phẩm TikTok Shop (tên, giá, ảnh, mô tả, thông số) bằng code sẵn của Tt Affiliate.
    Dùng kết quả để tự viết hook và lời đọc, rồi gọi create_product_video với narrations."""
    import subprocess
    import sys
    root = _affiliate_root()
    py = root / ".venv" / "bin" / "python"
    code = ("import json,sys;sys.path.insert(0,'.');import product_sources as p;"
            "print(json.dumps(p.fetch_tiktok_product(sys.argv[1]),ensure_ascii=False,default=str))")
    r = subprocess.run([str(py if py.exists() else sys.executable), "-c", code, url], cwd=str(root),
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("TikTok tạm chặn đọc tự động từ link này: " + r.stderr.strip()[-500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _read_json(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
