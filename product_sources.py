"""
Product inputs for demo.py: a Google Sheet tab and public TikTok Shop product pages.

Sheet layout: row 1 holds the column names in SHEET_COLUMNS, one product per row after it.
The service account in google-credentials.json needs Editor access to the sheet.
"""
import json
import re
import urllib.request

SHEET_COLUMNS = ["name", "price", "category", "images", "selling_points", "product_url",
                 "commission_pct", "sold_count", "notes", "status"]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
IMAGE_HOST = "https://p16-oec-sg.ibyteimg.com/"


def sheet_id_from(ref: str) -> str:
    """Accept a full Google Sheets link or a bare sheet ID."""
    m = re.search(r"/spreadsheets/d/([\w-]+)", ref or "")
    return m.group(1) if m else (ref or "").strip()


class ProductSheet:
    def __init__(self, sheet_ref: str, tab: str, credentials: str = "google-credentials.json"):
        import gspread

        book = gspread.service_account(filename=credentials).open_by_key(sheet_id_from(sheet_ref))
        self.ws = book.worksheet(tab)
        values = self.ws.get_all_values()
        self.header = [h.strip() for h in values[0]] if values else []
        missing = [c for c in SHEET_COLUMNS if c not in self.header]
        if missing:
            raise ValueError(f"Sheet '{tab}' row 1 is missing columns: {', '.join(missing)}")
        width = len(self.header)
        self.rows = [
            {"_row": i + 2, **dict(zip(self.header, (r + [""] * width)[:width]))}
            for i, r in enumerate(values[1:])
        ]

    def pending(self) -> list:
        """Rows with a name or product link and an empty status (done, skip, needs_images are left alone)."""
        return [r for r in self.rows
                if (r["name"].strip() or r["product_url"].strip()) and not r["status"].strip()]

    def find_by_url(self, url: str):
        return next((r for r in self.rows if url and r["product_url"].strip() == url.strip()), None)

    def update(self, row: dict, values: dict) -> None:
        from gspread import Cell

        cells = [Cell(row["_row"], self.header.index(k) + 1, v) for k, v in values.items()]
        if cells:
            self.ws.update_cells(cells)
            row.update(values)


def _vnd(text) -> int:
    digits = re.sub(r"[^\d]", "", str(text or ""))
    return int(digits) if digits else 0


def fetch_tiktok_product(url: str) -> dict:
    """Read a public TikTok Shop product page (share link or pdp link).

    Returns title, lowest price, sold count, original-size image URLs, description text
    and specifications. Commission is not on the public page.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "vi-VN,vi;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", "replace")

    m = re.search(r'id="__MODERN_ROUTER_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("TikTok returned no product data (captcha or page layout changed)")
    loader = json.loads(m.group(1)).get("loaderData", {})
    page = next((v for k, v in loader.items() if "/pdp/" in k and isinstance(v, dict)), {})
    components = (page.get("page_config") or {}).get("components_map", [])
    info = next((c["component_data"]["product_info"] for c in components
                 if (c.get("component_data") or {}).get("product_info")), None)
    if not info:
        raise RuntimeError("Product data not found on the page")

    lines = []
    for block in info.get("desc_blocks", []):
        if block.get("type") == "text" and block.get("text"):
            lines.append(block["text"].strip())
        elif block.get("type") == "ul":
            lines += [f"- {x.strip()}" for x in block.get("content", []) if isinstance(x, str)]

    price = info.get("price") or {}
    return {
        "title": (info.get("title") or "").strip(),
        "price": _vnd(price.get("min_sku_price")),
        "original_price": _vnd(price.get("min_sku_original_price")),
        "sold_count": info.get("sold_count") or 0,
        "images": [f"{IMAGE_HOST}{img['uri']}~tplv-aphluv4xwc-origin-jpeg.jpeg"
                   for img in info.get("images", []) if img.get("uri")],
        "description": "\n".join(lines),
        "specs": [f"{s['name']}: {s['value']}" for s in info.get("specifications", [])
                  if s.get("name") and s.get("value")],
    }
