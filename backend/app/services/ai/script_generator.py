"""
AI Script Generator - tạo kịch bản video TikTok từ thông tin sản phẩm
"""
import json
from openai import AsyncOpenAI
from app.core.config import settings


client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


PRODUCT_VIDEO_SYSTEM_PROMPT = """Bạn là chuyên gia content TikTok người Việt, chuyên tạo kịch bản video ngắn viral cho affiliate marketing.
Viết kịch bản tự nhiên, gần gũi, phù hợp với người dùng TikTok Việt Nam tuổi 18-35.
Luôn trả về JSON hợp lệ theo schema được yêu cầu."""


async def generate_product_script(product: dict) -> dict:
    """
    Tạo kịch bản video từ thông tin sản phẩm Shopee.
    
    Args:
        product: dict chứa name, price, description, category, discount_percent
    
    Returns:
        dict: {hook, script_segments, voiceover_text, hashtags, caption}
    """
    discount_info = ""
    if product.get("discount_percent", 0) > 0:
        discount_info = f"Giảm {product['discount_percent']:.0f}% còn {product['price']:,.0f}đ"

    user_prompt = f"""Tạo kịch bản TikTok 30-45 giây cho sản phẩm sau:

Tên: {product['name']}
Danh mục: {product.get('category', 'Đồ dùng')}
Giá: {product.get('price', 0):,.0f}đ
{discount_info}
Mô tả: {product.get('description', '')[:300]}

Trả về JSON với cấu trúc:
{{
    "hook": "câu mở đầu gây chú ý (max 10 chữ, dạng câu hỏi hoặc gây shock)",
    "problem": "vấn đề người xem đang gặp (1-2 câu)",
    "solution": "sản phẩm giải quyết như thế nào (2-3 câu)",
    "benefits": ["lợi ích 1", "lợi ích 2", "lợi ích 3"],
    "cta": "câu kêu gọi hành động cuối video",
    "voiceover_text": "toàn bộ text đọc liên tục cho TTS, tự nhiên như người thật nói",
    "hashtags": ["hashtag1", "hashtag2", ...],
    "caption": "caption cho post TikTok (max 150 ký tự)"
}}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PRODUCT_VIDEO_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.8
    )

    return json.loads(response.choices[0].message.content)


async def generate_lifestyle_script(topic: str, related_product: dict = None) -> dict:
    """
    Tạo kịch bản video lifestyle/tips có thể kết hợp quảng cáo sản phẩm nhẹ nhàng.
    
    Args:
        topic: chủ đề (vd: "mẹo dọn nhà nhanh", "tips tiết kiệm tiền")
        related_product: sản phẩm liên quan để mention tự nhiên (optional)
    """
    product_mention = ""
    if related_product:
        product_mention = f"""
Cuối video mention tự nhiên sản phẩm: {related_product['name']} (giá {related_product.get('price', 0):,.0f}đ)
Không quảng cáo lộ liễu, chỉ gợi ý như một giải pháp."""

    user_prompt = f"""Tạo kịch bản TikTok lifestyle 45-60 giây về chủ đề: {topic}
{product_mention}

Video phải thực sự hữu ích, không cảm giác quảng cáo.
Trả về JSON:
{{
    "hook": "câu mở đầu gây tò mò (max 10 chữ)",
    "tips": ["tip 1", "tip 2", "tip 3"],
    "product_mention": "câu mention sản phẩm tự nhiên (nếu có, không thì null)",
    "voiceover_text": "toàn bộ text đọc cho TTS",
    "hashtags": ["hashtag1", ...],
    "caption": "caption ngắn gọn cho post"
}}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PRODUCT_VIDEO_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.9
    )

    return json.loads(response.choices[0].message.content)


async def generate_voiceover(text: str, output_path: str) -> str:
    """
    Tạo file audio giọng đọc từ text sử dụng OpenAI TTS.
    
    Returns: path đến file audio
    """
    response = await client.audio.speech.create(
        model="tts-1",
        voice="nova",       # nova: giọng nữ trẻ, tự nhiên
        input=text,
        speed=1.1           # hơi nhanh hơn cho TikTok
    )

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path
