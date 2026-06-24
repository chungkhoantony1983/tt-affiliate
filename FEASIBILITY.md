# Đánh Giá Tính Khả Thi — TikTok Affiliate Automation

> **Ngày đánh giá**: 2026-06-24  
> **Bối cảnh**: 1,100+ followers, có store Shopee affiliate, N8N trên desktop nhà.
> **Ràng buộc chi phí**: Claude Pro $20/tháng + có thể dùng thêm Antigravity Pro.

---

## Câu Hỏi Nhanh Trước Khi Đọc

### ❓ Claude Pro $20/tháng có dùng được cho automation không?

**Không trực tiếp.**

| | Claude.ai Pro ($20/mo) | Claude API |
|--|---|---|
| Truy cập qua | Web browser | HTTP API (code/N8N) |
| Tính phí | Flat $20/tháng | Pay-per-token |
| Dùng trong N8N | ❌ Không thể | ✅ Được |
| Dùng cho review thủ công | ✅ Tốt nhất | ❌ Không tiện |

**Kết luận**: Claude Pro dùng để **review quality thủ công**, không phải để automate.  
Automation cần Groq (free) hoặc Gemini (free) hoặc Claude API (separate billing).

---

### ❓ OpenAI free account có lấy được API không?

**Có API key nhưng cần nạp tiền mới dùng được.**

- Tạo API key: ✅ Được (dashboard.openai.com)
- Gọi API không có credit: ❌ Báo lỗi 429 "Insufficient quota"
- Nạp tối thiểu: $5 để bắt đầu dùng
- OpenAI TTS (giọng đọc): ~$0.015/1K chars → **$3-5/tháng** nếu tạo 200 video/tháng

**Kết luận**: Nếu muốn dùng OpenAI TTS, cần nạp tối thiểu $5. Hoặc dùng `edge-tts` miễn phí.

---

### ❓ Google Antigravity Pro là gì?

**Google Antigravity** ([antigravity.google](https://antigravity.google/)) là **agentic development platform** của Google:

| Feature | Mô tả |
|---------|--------|
| **Antigravity IDE** | Full-featured IDE với AI agent tích hợp, hiểu context codebase |
| **Antigravity CLI** | Terminal-first agent, chạy autonomous coding, shell commands |
| **Antigravity SDK** | Python scripts để build custom agents trên harness của Antigravity |
| **Antigravity 2.0** | Command center: quản lý multiple agents song song, scheduled messages |
| **Giá** | **Miễn phí** ("Available at no charge") |

**Vai trò trong dự án này**:
- ✅ Dùng làm **development IDE** thay/bổ sung VS Code — được Google Gemini hỗ trợ viết code
- ✅ Dùng Antigravity CLI để **automate development tasks** (code generation, testing)
- ✅ Dùng Antigravity SDK để **prototype custom agents** cho video pipeline
- ✅ Gemini models tích hợp sẵn → có thể dùng **thay thế Groq** cho script generation
- ❌ Không phải hosting platform — vẫn cần N8N cho scheduling/orchestration

**Kết luận**: Antigravity Pro là **development tool** (miễn phí) giúp code nhanh hơn + có access Gemini models.
Kết hợp Claude Pro (reasoning/review) + Antigravity (coding/Gemini access) = **$20/tháng total** cho toàn bộ AI development power.

---

## Ba Phương Án Triển Khai

---

## 🅰️ Phương Án A: Local-First (Zero API Cost)

**Triết lý**: Chạy mọi thứ trên desktop nhà, dùng free tools tối đa.

### Stack

| Component | Tool | Chi phí |
|-----------|------|---------|
| Automation | N8N (self-hosted Docker) | **$0** |
| LLM script gen | Ollama + Qwen2.5 7B (local) | **$0** |
| TTS voiceover | edge-tts (Microsoft free) | **$0** |
| Video render | FFmpeg + MoviePy (local) | **$0** |
| DB + Queue | PostgreSQL + Redis (Docker) | **$0** |
| Dashboard | Streamlit (local) | **$0** |
| Quality review | Claude.ai Pro (manual) | **$20/tháng** |
| **Tổng** | | **~$20-25/tháng** |

### Workflow

```
N8N (9h sáng)
 → Lấy sản phẩm từ DB
 → Gọi Backend API (Ollama local → script)
 → edge-tts (voiceover)
 → FFmpeg (render)
 → TikTok API (upload)
 → Telegram (notify)
```

### Yêu cầu máy

| | Tối thiểu | Thoải mái |
|--|--|--|
| RAM | 8GB | 16GB |
| GPU | Không bắt buộc | GPU 6GB+ giúp render nhanh |
| CPU | 4 cores | 8 cores |
| Ollama + Qwen2.5 7B | ~4.5GB VRAM hoặc chạy CPU | |

### SWOT — Phương Án A

| | 👍 Strengths | 👎 Weaknesses |
|--|--|--|
| | Chi phí cố định thấp nhất ($20/tháng) | Script quality phụ thuộc local model |
| | Không phụ thuộc cloud API | Máy phải bật 24/7 |
| | Privacy cao (data không ra ngoài) | Render chậm hơn (CPU) |
| | Không bị rate limit | Ollama cần setup phức tạp hơn |

| | 🚀 Opportunities | ⚠️ Threats |
|--|--|--|
| | Nâng GPU → quality AI video tốt hơn | Mất điện = dừng automation |
| | Thêm model mới local miễn phí | Model local tệ hơn GPT-4o |
| | Chạy nhiều video song song nếu máy mạnh | Video quality có thể không đủ để convert |

**Phù hợp khi**: Máy desktop mạnh (16GB RAM, có GPU), muốn chi phí tối thiểu.

---

## 🅱️ Phương Án B: Hybrid (Khuyến nghị ⭐)

**Triết lý**: Dùng free tier cloud API cho automation, Claude Pro cho review.
**Target chi phí**: $20-35/tháng.

### Stack

| Component | Tool | Chi phí |
|-----------|------|---------|
| Automation | N8N (self-hosted) | **$0** |
| LLM bulk | Groq API free (Llama 3.1 70B) | **$0** |
| LLM fallback | Gemini 1.5 Flash free tier | **$0** |
| TTS | edge-tts (free) | **$0** |
| Video render | FFmpeg local | **$0** |
| Quality review | Claude.ai Pro (manual) | **$20/tháng** |
| OpenAI TTS (optional) | nếu muốn quality tốt hơn | **$3-5/tháng** |
| DB + Queue | PostgreSQL + Redis (Docker) | **$0** |
| **Tổng** | | **$20-25/tháng** |

### Groq Free Tier Limits

```
Llama 3.1 70B:
- 30 requests/minute
- 14,400 requests/day (= 14,400 scripts/ngày!)
- Latency: ~0.5-2s/request (rất nhanh)

→ Đủ để tạo script cho 200+ video/tháng với margin lớn
```

### Gemini Free Tier Limits

```
Gemini 1.5 Flash:
- 15 RPM (requests per minute)
- 1,500 RPM daily
- 1M tokens/day

→ Dùng làm fallback khi Groq gặp sự cố
```

### SWOT — Phương Án B

| | 👍 Strengths | 👎 Weaknesses |
|--|--|--|
| | Script quality cao hơn A (Llama 70B > 7B) | Phụ thuộc internet cho Groq/Gemini |
| | Groq cực nhanh (0.5-2s/script) | Free tier có thể bị thay đổi policy |
| | Chi phí cố định thấp ($20-25/tháng) | Cần backup plan nếu free tier bị giới hạn |
| | Không cần GPU mạnh | |

| | 🚀 Opportunities | ⚠️ Threats |
|--|--|--|
| | Upgrade từng service khi revenue tăng | Groq có thể giảm/remove free tier |
| | Thêm OpenAI TTS dễ dàng ($5/tháng) | Gemini API policy thay đổi |
| | Scale lên số lượng video dễ | |

**Phù hợp khi**: Muốn bắt đầu nhanh, chi phí thấp, máy không có GPU mạnh.

---

## 🆒 Phương Án C: Full Quality SaaS

**Triết lý**: Đầu tư vào chất lượng để tăng conversion rate.
**Target chi phí**: $80-150/tháng.

### Stack

| Component | Tool | Chi phí |
|-----------|------|---------|
| Automation | N8N (self-hosted) | **$0** |
| LLM | Claude API (Haiku 3.5) | **~$10-20/tháng** |
| TTS | ElevenLabs Starter | **$5/tháng** |
| Video AI clips | Kling AI Basic | **$20-50/tháng** |
| Video render | FFmpeg + Kling hybrid | **$0** (local) |
| Quality review | Claude.ai Pro | **$20/tháng** |
| DB + infra | Docker local | **$0** |
| **Tổng** | | **$55-95/tháng** |

### Khi nào dùng Claude API thay Groq:

```python
# Smart routing
def choose_llm(task_type: str) -> str:
    if task_type == "bulk_script":
        return "groq"   # 300 scripts/tháng = $0
    elif task_type == "quality_review":
        return "claude_haiku"  # 20 scripts/tháng = ~$0.02
    elif task_type == "complex_strategy":
        return "claude_sonnet"  # Manual qua web
```

### SWOT — Phương Án C

| | 👍 Strengths | 👎 Weaknesses |
|--|--|--|
| | Video AI chất lượng cao → CTR tốt hơn | Chi phí cao, cần revenue bù đắp |
| | ElevenLabs: giọng đọc rất tự nhiên | Phụ thuộc nhiều SaaS |
| | Claude API: script nhất quán, không hallucinate | Kling AI còn beta, có thể không ổn định |

| | 🚀 Opportunities | ⚠️ Threats |
|--|--|--|
| | High-quality content → viral nhanh | $80-150/tháng cần affiliate revenue cover |
| | AI video clips nổi bật hơn slideshow | Nếu không có revenue trong 3 tháng → lỗ |

**Phù hợp khi**: Đã có revenue từ affiliate, muốn scale nhanh và nghiêm túc.

---

## So Sánh Tổng Hợp

| Tiêu chí | Phương án A | Phương án B ⭐ | Phương án C |
|---------|-------------|----------------|-------------|
| **Chi phí/tháng** | $20-25 | $20-25 | $55-95 |
| **Script quality** | Trung bình (local) | Tốt (Llama 70B) | Tốt nhất (Claude) |
| **Video quality** | Cơ bản | Cơ bản | AI-enhanced |
| **Setup difficulty** | Cao (Ollama) | Thấp | Trung bình |
| **Phụ thuộc internet** | Thấp | Trung bình | Cao |
| **Scalability** | Giới hạn bởi máy | Tốt | Tốt nhất |
| **Break-even point** | ~5-10 đơn/tháng | ~5-10 đơn/tháng | ~20-30 đơn/tháng |
| **Rủi ro chính** | Máy yếu/mất điện | Free tier bị giới hạn | Chi phí cố định cao |

---

## SWOT Tổng Thể Dự Án

### 💪 Strengths (Điểm mạnh)
- Đã có 1,100+ followers → không bắt đầu từ 0
- Store Shopee sẵn có với sản phẩm đã chuẩn
- N8N self-hosted = không tốn server cost
- Groq/Gemini free tier đủ để chạy scale lớn
- Desktop nhà = không lo server uptime cost

### 🤝 Weaknesses (Điểm yếu)
- 1,100 followers chưa đủ để earn significant từ affiliate
- Cần > 5,000 followers để earn ổn định trên TikTok
- Chất lượng video AI vẫn kém hơn human-made
- TikTok algorithm ưu tiên consistency (cần đăng đều)
- Desktop phụ thuộc điện và internet tại nhà

### 🚀 Opportunities (Cơ hội)
- Thị trường affiliate VN đang tăng trưởng mạnh 2024-2026
- TikTok Shop tích hợp trực tiếp với affiliate → click-to-buy dễ hơn
- Automation = có thể tạo 30+ video/tháng (human làm 8-10)
- Lifestyle content có thể viral bất kể số follower
- AI tools ngày càng rẻ hơn và tốt hơn

### ⚠️ Threats (Rủi ro)
- TikTok thay đổi API → automation bị break
- Shopee affiliate commission có thể giảm
- TikTok có thể restrict automation/bot behavior
- Free tier của Groq/Gemini có thể bị giới hạn
- Cạnh tranh ngày càng nhiều affiliator dùng AI

---

## Khuyến Nghị

### Giai đoạn 1 (Tháng 1-2): **Phương Án B — Hybrid**

```
Chi phí: ~$20-25/tháng
Mục tiêu: Build system, test content formats
KPI: 30 videos/tháng, tăng từ 1,100 → 2,000 followers
```

**Bước cụ thể**:
1. Setup N8N Docker trên desktop
2. Đăng ký Groq API (free), edge-tts
3. Build pipeline: Shopee sync → script gen → render → upload
4. Test với 5-10 video manual trước khi tự động hóa
5. Dùng Claude.ai Pro để review script quality đầu tiên

### Giai đoạn 2 (Tháng 3-4): Optimize

```
KPI: Tìm ra top 3 category/format → double down
Upgrade: Thêm OpenAI TTS ($5/tháng) nếu muốn voice tốt hơn
```

### Giai đoạn 3 (Tháng 5+): **Phương Án C nếu ROI dương**

```
Điều kiện: Affiliate revenue > $80/tháng
Action: Upgrade sang ElevenLabs + Claude API + video AI clips
```

---

## Milestone & ROI Estimate

| Milestone | Followers | Videos/tháng | Est. Revenue/tháng |
|-----------|-----------|--------------|-------------------|
| **Hiện tại** | 1,100 | 0 (manual) | ~0₫ |
| **Tháng 1** | 2,000 | 30 | ~100,000-500,000₫ |
| **Tháng 3** | 5,000 | 60 | ~500,000-2,000,000₫ |
| **Tháng 6** | 10,000+ | 90 | ~2,000,000-5,000,000₫ |

> **Lưu ý**: Revenue từ Shopee Affiliate thường 1-5% commission.
> Sản phẩm $100,000₫ × 3% × 100 đơn/tháng = 300,000₫ commission.
> Cần volume đơn hàng cao để có revenue đáng kể.

---

## Kết Luận

**Bắt đầu với Phương Án B (Hybrid)**:
- Chi phí $20-25/tháng (về cơ bản chỉ là Claude Pro subscription đang có)
- Groq free tier đủ mạnh để tạo script chất lượng tốt
- edge-tts miễn phí với giọng Việt tự nhiên
- N8N trên desktop nhà = zero server cost

**Upgrade dần** dựa trên revenue thực tế, không đầu tư quá nhiều trước khi có traction.

---

*Đánh giá v1.0 — 2026-06-24*
