import sys
import os
import asyncio

# Thêm đường dẫn gốc và thư mục backend vào sys.path để chạy script từ thư mục con
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from backend.app.services.intelligence.events_vn import VietnamEventEngine
from backend.app.services.ai.script_generator import generate_product_script
from backend.app.services.seo.article_generator import generate_seo_article, save_article

async def run_demo():
    print("=== BẮT ĐẦU CHẠY THỬ NGHIỆM AI WORKFLOW ===")
    
    # 1. Định nghĩa một sản phẩm mẫu (Giả lập việc đọc từ Google Sheets)
    product_name = "Máy hút bụi mini cầm tay không dây"
    product_price = 150000
    affiliate_link = "https://s.shopee.vn/demo12345"
    product_data = {
        "name": product_name,
        "category": "Đồ gia dụng",
        "price": product_price,
        "discount_percent": 30,
        "description": "Máy hút bụi mini cầm tay không dây, lực hút mạnh 9000Pa, sạc Type-C, hút sạch bụi bẩn trên bàn làm việc, ghế sofa, ô tô. Nhỏ gọn tiện lợi."
    }
    
    # 2. Phân tích sự kiện hiện tại
    print("\n[1/3] Đang phân tích sự kiện thị trường...")
    topic = VietnamEventEngine.suggest_seo_topic(product_name)
    print(f"-> Chủ đề SEO được đề xuất: {topic}")
    
    # 3. Tạo kịch bản Video TikTok (Chế độ Stock Meme)
    print("\n[2/3] Đang nhờ Gemini Pro tạo kịch bản Video TikTok...")
    try:
        video_script = await generate_product_script(product_data)
        print("\n--- KỊCH BẢN TIKTOK TẠO RA ---")
        print(f"Hook: {video_script.get('hook')}")
        print("Các phân cảnh:")
        for idx, segment in enumerate(video_script.get('script_segments', [])):
            print(f"  Cảnh {idx+1}:")
            print(f"    - Thoại: {segment.get('text')}")
            print(f"    - Visual: {segment.get('visual_prompt')}")
        print(f"\nCaption: {video_script.get('caption')}")
    except Exception as e:
        print(f"Lỗi tạo script: {e}")

    # 4. Tạo bài viết SEO cho Blogspot
    print("\n[3/3] Đang nhờ Gemini Pro viết bài chuẩn SEO cho meovat36524h.blogspot.com...")
    try:
        article_content = await generate_seo_article(topic, product_name, affiliate_link)
        saved_path = save_article(article_content, "demo_may_hut_bui")
        print(f"-> Đã lưu bài viết SEO thành công tại: {saved_path}")
        print("\nBạn có thể mở file trên ra, copy toàn bộ nội dung và dán vào Blogger!")
    except Exception as e:
        print(f"Lỗi tạo bài viết SEO: {e}")

    print("\n=== HOÀN TẤT ===")

if __name__ == "__main__":
    asyncio.run(run_demo())
