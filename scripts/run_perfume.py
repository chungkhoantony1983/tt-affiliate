raise SystemExit("Paused: Shopee work is on hold, see TODO.md")

import sys
import os
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from backend.app.services.ai.script_generator import generate_product_script
from backend.app.services.seo.article_generator import generate_seo_article, save_article

async def run():
    product_name = "Nước hoa ô tô kẹp cửa gió điều hoà cao cấp"
    product_price = 120000
    affiliate_link = "https://s.shopee.vn/9pcIiVgc7M"
    product_data = {
        "name": product_name,
        "category": "Phụ kiện ô tô",
        "price": product_price,
        "discount_percent": 15,
        "description": "Nước hoa ô tô kẹp cửa gió điều hoà, khử mùi hôi xe hiệu quả, chống say xe, tạo hương thơm sang trọng, dễ chịu. Giúp tinh thần tỉnh táo khi lái xe đường dài."
    }
    
    topic = "Bí quyết đánh bay mùi hôi xe, chống say xe hiệu quả và các tác dụng tuyệt vời của nước hoa ô tô"
    
    print("\n[1/2] Đang tạo kịch bản Video TikTok...")
    video_script = await generate_product_script(product_data)
    print("\n--- KỊCH BẢN TIKTOK ---")
    print(f"Hook: {video_script.get('hook')}")
    for idx, segment in enumerate(video_script.get('script_segments', [])):
        print(f"  Cảnh {idx+1}:")
        print(f"    - Thoại: {segment.get('text')}")
        print(f"    - Visual: {segment.get('visual_prompt')}")
    print(f"Caption: {video_script.get('caption')}")

    print("\n[2/2] Đang viết bài chuẩn SEO ngắn (tập trung vào tác dụng nước hoa ô tô)...")
    article_content = await generate_seo_article(topic, product_name, affiliate_link)
    saved_path = save_article(article_content, "nuoc_hoa_oto_seo")
    print(f"-> Đã lưu bài viết tại: {saved_path}")

if __name__ == "__main__":
    asyncio.run(run())
