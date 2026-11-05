raise SystemExit("Paused: Shopee work is on hold, see TODO.md")

import sys
import os
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from backend.app.services.ai.script_generator import generate_product_script
from backend.app.services.seo.article_generator import generate_seo_article, save_article

async def run():
    product_name = "Combo vali khung nhôm khóa sập, vali du lịch size 20/24/28, chống va đập"
    product_price = 430000
    affiliate_link = "https://s.shopee.vn/BRnENgXgu"
    product_data = {
        "name": product_name,
        "category": "Thể thao & Du lịch",
        "price": product_price,
        "discount_percent": 0,
        "description": "Combo vali du lịch khung nhôm khóa sập siêu bền, chống va đập cực tốt, bảo hành 1 đổi 1. Đủ size 20/24/28, nhiều màu sắc thời trang (đen, trắng, bạc, xanh, hồng, vàng). Giá siêu hời chỉ hơn 400k."
    }
    
    topic = "Kinh nghiệm chọn mua vali du lịch bền đẹp, giá rẻ, chống quăng quật ở sân bay"
    
    print("\n[1/2] Đang tạo kịch bản Video TikTok...")
    video_script = await generate_product_script(product_data)
    print("\n--- KỊCH BẢN TIKTOK ---")
    print(f"Hook: {video_script.get('hook')}")
    for idx, segment in enumerate(video_script.get('script_segments', [])):
        print(f"  Cảnh {idx+1}:")
        print(f"    - Thoại: {segment.get('text')}")
        print(f"    - Visual: {segment.get('visual_prompt')}")
    print(f"Caption: {video_script.get('caption')}")

    print("\n[2/2] Đang viết bài chuẩn SEO ngắn (tập trung vào vali du lịch, chống va đập)...")
    article_content = await generate_seo_article(topic, product_name, affiliate_link)
    saved_path = save_article(article_content, "vali_du_lich_seo")
    print(f"-> Đã lưu bài viết tại: {saved_path}")

if __name__ == "__main__":
    asyncio.run(run())
