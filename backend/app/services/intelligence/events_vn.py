"""
Event Intelligence Engine - Dự báo nhu cầu theo lịch sự kiện Việt Nam.
"""
from datetime import datetime
from typing import List, Dict

class VietnamEventEngine:
    """
    Mapping các sự kiện, mùa và ngày lễ tại Việt Nam với danh mục sản phẩm Affiliate.
    Hệ thống sẽ dựa vào thời gian hiện tại để đề xuất (hoặc ưu tiên) các ngách sản phẩm phù hợp.
    """
    
    # Định nghĩa các sự kiện trong năm và ngách sản phẩm tương ứng
    EVENTS_CALENDAR = {
        "mùa_mưa_bão": {
            "months": [6, 7, 8, 9], # Tháng 6 đến 9
            "keywords": ["đi mưa", "chống nước", "tiện lợi mùa mưa", "vệ sinh xe"],
            "recommended_products": [
                "Thiết bị xe máy (áo mưa, bọc giày, xịt chống bám nước)",
                "Đồ gia dụng (máy sấy quần áo mini, móc phơi thông minh)",
                "Phụ kiện điện thoại (túi chống nước điện thoại)"
            ]
        },
        "mùa_du_lịch_dã_ngoại": {
            "months": [5, 6, 7], # Nghỉ hè
            "keywords": ["cắm trại", "dã ngoại", "tiện lợi mang theo", "du lịch"],
            "recommended_products": [
                "Camera mini (quay vlog, gắn mũ bảo hiểm)",
                "Tai nghe, Sạc nhanh, Pin dự phòng",
                "Giá đỡ điện thoại (chụp ảnh, quay video xa)",
                "Máy cạo lông (làm đẹp đi biển)",
                "Máy lọc nước mini (cắm trại)"
            ]
        },
        "back_to_school": {
            "months": [8, 9], # Tựu trường
            "keywords": ["góc học tập", "nhập học", "sinh viên", "giá rẻ"],
            "recommended_products": [
                "Giá đỡ laptop, Giá đỡ điện thoại",
                "Đồ công nghệ giá rẻ (Cáp, Sạc, Tai nghe)",
                "Máy hút bụi mini (dọn phòng trọ, bàn học)"
            ]
        },
        "lễ_quốc_khánh_2_9": {
            "months": [8, 9], # Cuối tháng 8, đầu tháng 9
            "keywords": ["nghỉ lễ dài", "về quê", "du lịch lễ"],
            "recommended_products": [
                "Máy matxa cổ, gáy (quà tặng người lớn, hoặc dùng khi đi tàu xe)",
                "Tai nghe, sạc nhanh (giải trí trên xe)"
            ]
        },
        "trung_thu": {
            "months": [9, 10], # Khoảng tháng 8-8 Âm lịch (T9-10 Dương)
            "keywords": ["trung thu", "đoàn viên", "quà tặng", "gia đình"],
            "recommended_products": [
                "Đồ nhà bếp (dụng cụ làm bánh, bếp nướng mini)",
                "Máy matxa cổ, gáy (quà biếu ông bà bố mẹ)",
                "Máy vệ sinh tai (chăm sóc gia đình)"
            ]
        },
        "mega_sale_cuoi_nam": {
            "months": [10, 11, 12], # 10/10, 11/11, 12/12, Black Friday
            "keywords": ["săn sale", "xả hàng", "giá hủy diệt"],
            "recommended_products": [
                "Đồ gia dụng tổng hợp",
                "Phụ kiện điện thoại",
                "Đồ công nghệ giá rẻ"
            ]
        },
        "tet_nguyen_dan": {
            "months": [1, 2], # Tháng 1, 2
            "keywords": ["dọn nhà đón tết", "nấu ăn ngày tết", "quà tết"],
            "recommended_products": [
                "Máy hút bụi mini (dọn góc sofa, bàn thờ)",
                "Đồ nhà bếp (dụng cụ cắt tỉa, gọt vỏ)",
                "Máy matxa cổ gáy (quà biếu tết)"
            ]
        }
    }

    @classmethod
    def get_current_opportunities(cls) -> List[Dict]:
        """
        Lấy các cơ hội (opportunities) tương ứng với tháng hiện tại.
        """
        current_month = datetime.now().month
        opportunities = []
        
        for event_name, data in cls.EVENTS_CALENDAR.items():
            if current_month in data["months"]:
                opportunities.append({
                    "event_name": event_name.replace("_", " ").title(),
                    "keywords": data["keywords"],
                    "recommended_products": data["recommended_products"]
                })
                
        return opportunities

    @classmethod
    def suggest_seo_topic(cls, product_name: str) -> str:
        """
        Đề xuất topic viết bài SEO dựa trên thời điểm hiện tại và tên sản phẩm.
        """
        current_opps = cls.get_current_opportunities()
        if not current_opps:
            return f"Review chi tiết {product_name} - Có đáng mua không?"
            
        # Lấy event nổi bật nhất hiện tại (phần tử đầu)
        main_event = current_opps[0]
        context = main_event["event_name"]
        
        return f"Mẹo chuẩn bị cho {context} hoàn hảo - Giải pháp với {product_name}"
