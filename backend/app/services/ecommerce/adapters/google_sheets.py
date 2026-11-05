"""
Google Sheets Adapter — Đọc danh sách link sản phẩm từ Google Spreadsheet.
Dùng Service Account để kết nối.
"""
import logging
from typing import List
from dataclasses import dataclass
import gspread
from google.oauth2.service_account import Credentials

from app.core.config import settings
from .base import EcommerceAdapter, ProductData

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GoogleSheetsAdapter(EcommerceAdapter):
    """
    Adapter để đọc danh sách sản phẩm cần làm video từ Google Sheets.
    Cấu trúc bảng dự kiến:
    Col A: # (STT)
    Col B: Link sản phẩm
    Col C: Trạng thái (mới | queue | ready | uploaded video)
    Col D: Tên sản phẩm (tùy chọn)
    """

    def __init__(self):
        self.credentials_file = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', None)
        self.spreadsheet_id = getattr(settings, 'SPREADSHEET_ID', None)
        self.client = None
        self.sheet = None

    @property
    def platform_name(self) -> str:
        return "google_sheets"

    def is_configured(self) -> bool:
        return bool(self.credentials_file and self.spreadsheet_id)

    def _connect(self):
        if not self.client and self.is_configured():
            try:
                credentials = Credentials.from_service_account_file(
                    self.credentials_file, scopes=SCOPES
                )
                self.client = gspread.authorize(credentials)
                self.sheet = self.client.open_by_key(self.spreadsheet_id).sheet1
            except Exception as e:
                logger.error(f"Failed to connect to Google Sheets: {e}")

    def fetch_products(self, limit: int = 200) -> List[ProductData]:
        """Đọc các dòng có trạng thái 'mới'"""
        if not self.is_configured():
            logger.warning("Google Sheets not configured.")
            return []

        self._connect()
        if not self.sheet:
            return []

        try:
            records = self.sheet.get_all_records()
        except Exception as e:
            logger.error(f"Error reading records from sheets: {e}")
            return []

        products = []
        for row_idx, row in enumerate(records, start=2): # +2 to account for 0-index and header row
            status = str(row.get('Trạng thái', '')).lower().strip()
            if status == 'mới' and len(products) < limit:
                url = str(row.get('Link sản phẩm', '')).strip()
                if not url:
                    continue
                
                # Cập nhật trạng thái thành 'queue'
                try:
                    self.sheet.update_cell(row_idx, 3, 'queue') # Giả định Cột C là Trạng thái
                except Exception as e:
                    logger.error(f"Error updating status to queue for row {row_idx}: {e}")
                
                # Tạo ProductData (Thực tế cần cào thêm thông tin từ URL nếu URL là link sản phẩm)
                product = ProductData(
                    source_platform=self.platform_name,
                    source_item_id=f"gsheets_{row_idx}",
                    name=str(row.get('Tên sản phẩm', f"Sản phẩm {row_idx}")),
                    price=0.0,
                    source_url=url,
                    affiliate_link=url, # Với workflow này, URL thường đã là link affiliate dạng s.shopee.vn
                    is_active=True
                )
                products.append(product)

        logger.info(f"Fetched {len(products)} new products from Google Sheets.")
        return products

    def generate_affiliate_link(self, item_id: str) -> str:
        """Trong workflow Google Sheets, link đã được tạo sẵn bằng tay ở Col B."""
        return ""

    def update_status(self, item_id: str, new_status: str):
        """Cập nhật trạng thái lại vào Google Sheets"""
        if not self.sheet or not item_id.startswith('gsheets_'):
            return
        try:
            row_idx = int(item_id.split('_')[1])
            self.sheet.update_cell(row_idx, 3, new_status) # Cột C
            logger.info(f"Updated row {row_idx} status to {new_status}")
        except Exception as e:
            logger.error(f"Error updating status: {e}")
