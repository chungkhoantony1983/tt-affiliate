"""
SEO Article Generator — Tạo bài viết SEO cho Website (Markdown/HTML) kết hợp link Affiliate.
Sử dụng Gemini Pro 1.5.
"""
import os
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

SEO_ARTICLE_SYSTEM_PROMPT = """Bạn là một chuyên gia viết content SEO và Affiliate Marketing.
Nhiệm vụ của bạn là viết các bài blog chia sẻ kinh nghiệm, mẹo vặt cuộc sống (đồ gia dụng, công nghệ, dã ngoại...) 
sao cho tự nhiên, mang lại giá trị thực sự cho người đọc, đồng thời khéo léo chèn link sản phẩm Affiliate vào bài.

Yêu cầu bài viết:
1. Độ dài khoảng 500 - 700 chữ.
2. Chuẩn SEO: Có tiêu đề (H1), các mục con (H2, H3), sử dụng in đậm, in nghiêng hợp lý.
3. Văn phong: Gần gũi, chia sẻ trải nghiệm thực tế, dễ đọc.
4. Trả về kết quả dưới định dạng Markdown (.md) hợp lệ.
5. Ở đầu bài viết, luôn có đoạn YAML frontmatter chứa: title, description, keywords, date."""

async def generate_seo_article(topic: str, product_name: str, affiliate_link: str) -> str:
    """
    Tạo bài viết SEO giới thiệu sản phẩm một cách tự nhiên.
    """
    user_prompt = f"""Hãy viết một bài blog SEO về chủ đề: "{topic}"

Trong bài viết, hãy khéo léo nhắc đến sản phẩm "{product_name}" như một giải pháp hữu ích.
Chèn link Affiliate sau vào chỗ nhắc đến sản phẩm: {affiliate_link}

Vui lòng viết bằng Markdown và có frontmatter ở đầu bài."""

    response = model.generate_content(
        contents=[
            {"role": "user", "parts": [SEO_ARTICLE_SYSTEM_PROMPT]},
            {"role": "user", "parts": [user_prompt]}
        ],
        generation_config={"temperature": 0.7}
    )

    return response.text

def save_article(content: str, filename: str):
    """Lưu bài viết ra file Markdown để đăng lên WordPress/Blogger sau này."""
    output_dir = os.path.join(settings.STORAGE_PATH, "seo_articles")
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"{filename}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path
