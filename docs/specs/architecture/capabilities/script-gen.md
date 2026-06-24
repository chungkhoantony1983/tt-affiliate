# Capability: script-gen

> **Mục đích**: Tạo kịch bản video TikTok (script + voiceover text + hashtags + caption)
> từ thông tin sản phẩm Shopee hoặc từ topic lifestyle.

---

## Overview

| | |
|--|--|
| **Input** | Product data (name, price, description, images, category) hoặc lifestyle topic |
| **Output** | JSON với: `hook`, `voiceover_text`, `hashtags[]`, `caption`, `benefits[]` |
| **SLA** | < 30 giây/script (Groq free) hoặc < 10 giây (Claude Haiku) |
| **Cost** | $0 (Groq free tier) → $0.001/script (Claude Haiku fallback) |

---

## Workflow

```
[Input: product_data hoặc topic]
        ↓
1. Chọn LLM theo load:
   - Groq free (default) → Llama 3.1 70B
   - Gemini Flash (fallback nếu Groq rate limit)
   - Claude Haiku (khi cần quality cao)
        ↓
2. Build prompt từ template (xem Prompt Templates bên dưới)
        ↓
3. Parse JSON output
        ↓
4. Validate: hook ≤ 10 chữ, voiceover_text ≤ 500 chữ, hashtags 5-10 cái
        ↓
5. Retry nếu parse fail (max 2 lần)
        ↓
[Output: script JSON → gửi cho video-render]
```

---

## Prompt Templates

### Template 1: Product Showcase

```
System: Bạn là chuyên gia TikTok content người Việt, tạo script viral cho affiliate.
Luôn trả về JSON hợp lệ.

User:
Tạo script TikTok 30-45 giây cho sản phẩm:
- Tên: {product.name}
- Giá: {product.price:,}đ {discount_text}
- Danh mục: {product.category}
- Mô tả: {product.description[:200]}

Trả về JSON:
{
  "hook": "câu mở đầu gây chú ý (max 10 chữ)",
  "problem": "vấn đề người xem gặp (1-2 câu)",
  "solution": "sản phẩm giải quyết như thế nào (2-3 câu)",
  "benefits": ["lợi ích 1", "lợi ích 2", "lợi ích 3"],
  "cta": "câu kêu gọi hành động",
  "voiceover_text": "text đọc liên tục tự nhiên cho TTS",
  "hashtags": ["tag1", "tag2", ...],
  "caption": "caption post TikTok (max 150 ký tự)"
}
```

### Template 2: Lifestyle Content

```
System: [như trên]

User:
Tạo script TikTok lifestyle 45-60 giây về: {topic}
{product_mention_instruction}

Trả về JSON:
{
  "hook": "câu mở đầu gây tò mò (max 10 chữ)",
  "tips": ["tip 1", "tip 2", "tip 3"],
  "product_mention": "câu mention sản phẩm tự nhiên hoặc null",
  "voiceover_text": "text đọc cho TTS",
  "hashtags": ["tag1", ...],
  "caption": "caption ngắn"
}
```

---

## LLM Configuration

```python
# Groq (default, free)
GROQ_MODEL = "llama-3.1-70b-versatile"
GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_TEMPERATURE = 0.8
GROQ_MAX_TOKENS = 800

# Fallback: Gemini Flash (free)
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_TEMPERATURE = 0.8

# High-quality: Claude Haiku
CLAUDE_MODEL = "claude-haiku-3-5"
CLAUDE_MAX_TOKENS = 800
```

---

## Error Handling

| Lỗi | Nguyên nhân | Xử lý |
|-----|-------------|-------|
| JSON parse error | LLM trả non-JSON | Retry với prompt nhắc "Chỉ trả về JSON" |
| Rate limit (Groq) | Vượt free tier | Fallback sang Gemini Flash |
| `hook` > 10 chữ | LLM không follow format | Truncate hoặc retry |
| Voiceover quá dài | > 500 chữ | Trim ở câu hoàn chỉnh |
| No product description | Shopee thiếu data | Dùng category + name để generate |

---

## Cost Notes

- **Groq free**: 30 requests/min, 14,400/day → đủ cho ~50 video/ngày
- **Gemini Flash free**: 15 RPM, 1M tokens/day → đủ cho fallback
- **Claude Haiku**: ~$0.001/script (800 tokens × $0.80/1M input + $4/1M output)
- **Target tháng**: 300 scripts → $0 (Groq) hoặc $0.30 (Claude Haiku nếu dùng all)

---

## Dependencies

- `shopee-sync` → cung cấp product data
- Groq API key (`GROQ_API_KEY`)
- Gemini API key (`GEMINI_API_KEY`)
- OpenAI/Anthropic API key (optional fallback)

---

## Files

```
backend/app/services/ai/
├── script_generator.py   ← implementation
├── prompt_templates/
│   ├── product_showcase.txt
│   └── lifestyle.txt
└── llm_router.py         ← chọn LLM theo priority/availability
```
