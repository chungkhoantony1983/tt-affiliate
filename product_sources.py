"""
Product inputs for demo.py: a Google Sheet tab and public TikTok Shop product pages.

Sheet layout: row 1 holds the column names in SHEET_COLUMNS, one product per row after it.
The service account in google-credentials.json needs Editor access to the sheet.
"""
import csv
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

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

    def get_row(self, row_num: int):
        """Return the row dict for 1-based sheet row number row_num (row 1 is the header)."""
        return next((r for r in self.rows if r["_row"] == row_num), None)

    def find_by_url(self, url: str):
        return next((r for r in self.rows if url and r["product_url"].strip() == url.strip()), None)

    def update(self, row: dict, values: dict) -> None:
        from gspread import Cell

        clean = {k: str(v) for k, v in values.items() if k in self.header}
        cells = [Cell(row["_row"], self.header.index(k) + 1, v) for k, v in clean.items()]
        if cells:
            self.ws.update_cells(cells)
            row.update(clean)


_REAL_PRODUCT_SHEET = ProductSheet


class CsvProductSheet:
    """Local CSV table with the same row numbering (row 1 = header, data from row 2) and API as ProductSheet."""

    def __init__(self, path: str):
        self.path = Path(path)
        with self.path.open(encoding="utf-8-sig", newline="") as f:
            raw_rows = list(csv.reader(f))
        self.header = [h.strip() for h in raw_rows[0]] if raw_rows else list(SHEET_COLUMNS)
        for col in SHEET_COLUMNS:
            if col not in self.header:
                self.header.append(col)
        width = len(self.header)
        self.rows = [
            {"_row": i + 2, **dict(zip(self.header, (r + [""] * width)[:width]))}
            for i, r in enumerate(raw_rows[1:])
        ]

    def pending(self) -> list:
        return [r for r in self.rows
                if (r["name"].strip() or r["product_url"].strip()) and not r["status"].strip()]

    def get_row(self, row_num: int):
        return next((r for r in self.rows if r["_row"] == row_num), None)

    def find_by_url(self, url: str):
        return next((r for r in self.rows if url and r["product_url"].strip() == url.strip()), None)

    def update(self, row: dict, values: dict) -> None:
        clean = {k: str(v) for k, v in values.items() if k in self.header}
        if not clean:
            return
        row.update(clean)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self.header)
            for r in self.rows:
                writer.writerow([r.get(h, "") for h in self.header])
        tmp.replace(self.path)


def open_product_sheet(sheet_ref: str = "", tab: str = "Tiktok",
                       credentials: str = "google-credentials.json", csv_path: str = ""):
    """Open Google Sheet when configured (or mocked), otherwise fall back to STUDIO_CSV_PATH / products.csv."""
    if ProductSheet is not _REAL_PRODUCT_SHEET:
        return ProductSheet(sheet_ref, tab, credentials)
    csv_file = (csv_path or os.environ.get("STUDIO_CSV_PATH") or "").strip()
    if csv_file:
        if not Path(csv_file).is_file():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        return CsvProductSheet(csv_file)
    ref = (sheet_ref or os.environ.get("SPREADSHEET_ID") or "").strip()
    if ref and Path(credentials).is_file():
        return ProductSheet(ref, tab, credentials)
    if Path("products.csv").is_file():
        return CsvProductSheet("products.csv")
    raise RuntimeError("Google Sheet is not configured")


def _vnd(text) -> int:
    digits = re.sub(r"[^\d]", "", str(text or ""))
    return int(digits) if digits else 0


def _og_info_fallback(*urls: str) -> dict:
    """Read title and main image from og_info query param on a redirected TikTok share URL."""
    for u in urls:
        if not u:
            continue
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlsplit(u).query)
            raw = (qs.get("og_info") or [None])[0]
            if not raw:
                continue
            try:
                og = json.loads(raw)
            except ValueError:
                og = json.loads(urllib.parse.unquote(raw))
        except Exception:
            continue
        if isinstance(og, dict):
            title = (og.get("title") or "").strip()
            image = (og.get("image") or "").strip()
            if title or image:
                return {
                    "title": title,
                    "price": _vnd(og.get("price")) if og.get("price") else 0,
                    "original_price": 0,
                    "sold_count": 0,
                    "images": [image] if image else [],
                    "description": (og.get("description") or "").strip(),
                    "specs": [],
                    "partial": True,
                }
    return {}


def fetch_tiktok_product(url: str) -> dict:
    """Read a public TikTok Shop product page (share link or pdp link).

    Returns title, lowest price, sold count, original-size image URLs, description text
    and specifications. Commission is not on the public page.
    If TikTok blocks __MODERN_ROUTER_DATA__ with a captcha, falls back to og_info on the
    redirected URL (with partial=True) before raising RuntimeError.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "vi-VN,vi;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        final_url = getattr(resp, "geturl", lambda: url)() or url
        html = resp.read().decode("utf-8", "replace")

    m = re.search(r'id="__MODERN_ROUTER_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        fallback = _og_info_fallback(final_url, url)
        if fallback:
            return fallback
        raise RuntimeError("TikTok returned no product data (captcha or page layout changed)")
    loader = json.loads(m.group(1)).get("loaderData", {})
    page = next((v for k, v in loader.items() if "/pdp/" in k and isinstance(v, dict)), {})
    components = (page.get("page_config") or {}).get("components_map", [])
    info = next((c["component_data"]["product_info"] for c in components
                 if (c.get("component_data") or {}).get("product_info")), None)
    if not info:
        fallback = _og_info_fallback(final_url, url)
        if fallback:
            return fallback
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
        "partial": False,
    }


# ---------------------------------------------------------------------------
# Travel tab (DR-0002): one question per row. Kept apart from ProductSheet on purpose (T-15).
# ---------------------------------------------------------------------------

TRAVEL_SHEET_COLUMNS = ["question", "destination", "audience", "pillar", "source_urls", "notes",
                        "facts_manual", "status"]


class TravelSheet:
    def __init__(self, sheet_ref: str, tab: str, credentials: str = "google-credentials.json"):
        import gspread

        book = gspread.service_account(filename=credentials).open_by_key(sheet_id_from(sheet_ref))
        self.ws = book.worksheet(tab)
        values = self.ws.get_all_values()
        self.header = [h.strip() for h in values[0]] if values else []
        missing = [c for c in TRAVEL_SHEET_COLUMNS if c not in self.header]
        if missing:
            raise ValueError(f"Sheet '{tab}' row 1 is missing columns: {', '.join(missing)}")
        width = len(self.header)
        self.rows = [
            {"_row": i + 2, **dict(zip(self.header, (r + [""] * width)[:width]))}
            for i, r in enumerate(values[1:])
        ]

    def pending(self) -> list:
        """Rows with a question and an empty status (done, skip, review, needs_sources are left alone)."""
        return [r for r in self.rows if r["question"].strip() and not r["status"].strip()]

    def find(self, question: str, destination: str = "", audience: str = ""):
        """Row matching the key stored in topic.json. A row with the exact destination / audience wins over a row
        whose cell is empty (empty cells match any); a different non-empty value never matches."""
        q = (question or "").strip()
        best, best_score = None, -1
        for r in self.rows:
            if r["question"].strip() != q:
                continue
            score = 0
            for want, cell in ((destination, r["destination"].strip()), (audience, r["audience"].strip())):
                if want and cell not in ("", want):
                    score = -1
                    break
                score += 1 if want and cell == want else 0
            if score > best_score:
                best, best_score = r, score
        return best if best_score >= 0 else None

    def update(self, row: dict, values: dict) -> None:
        from gspread import Cell

        cells = [Cell(row["_row"], self.header.index(k) + 1, v) for k, v in values.items()]
        if cells:
            self.ws.update_cells(cells)
            row.update(values)
