"""
N8N Workflow: Daily Product Video Generation
Lưu file này như một reference - import vào N8N qua UI

Workflow ID: daily-product-video
Mô tả: Mỗi ngày 9:00 SA, tự động tạo video cho 1-2 sản phẩm chưa có video
"""

WORKFLOW_DESCRIPTION = """
┌─────────────────────────────────────────────────────────────────┐
│  WORKFLOW: DAILY PRODUCT VIDEO GENERATOR                         │
│  Trigger: Cron (9:00 AM Asia/Ho_Chi_Minh)                        │
└─────────────────────────────────────────────────────────────────┘

Nodes:
1. [Cron Trigger]
   - Schedule: 0 9 * * * (9:00 AM mỗi ngày)
   - Timezone: Asia/Ho_Chi_Minh

2. [HTTP Request] → GET http://backend:8000/api/products/pending-video
   - Lấy sản phẩm chưa có video, sort by sales_count DESC
   - Limit: 2 sản phẩm/ngày

3. [IF] → Có sản phẩm không?
   - Yes → tiếp tục
   - No → [Telegram] "Không có sản phẩm mới cần làm video hôm nay"

4. [Split In Batches] → xử lý từng sản phẩm

5. [HTTP Request] → POST http://backend:8000/api/videos/create
   Body: { "product_id": "{{ $json.id }}", "content_type": "product_showcase" }
   → Trả về job_id

6. [Wait] → 5 phút (chờ render)

7. [HTTP Request] → GET http://backend:8000/api/videos/{{ job_id }}/status
   → Kiểm tra status

8. [IF] → status == "rendered"?
   - Yes → [HTTP Request] POST /api/videos/{{ job_id }}/upload
   - No → [Wait 2 phút] → retry check (max 5 lần)

9. [Telegram] → Thông báo kết quả
   "✅ Video đã đăng: [tên sản phẩm] - TikTok ID: [id]"
"""

# N8N Workflow JSON export (để import vào N8N)
WORKFLOW_JSON = {
    "name": "Daily Product Video Generator",
    "nodes": [
        {
            "name": "Cron Trigger",
            "type": "n8n-nodes-base.cron",
            "position": [250, 300],
            "parameters": {
                "triggerTimes": {
                    "item": [{"mode": "everyDay", "hour": 9, "minute": 0}]
                }
            }
        },
        {
            "name": "Get Pending Products",
            "type": "n8n-nodes-base.httpRequest",
            "position": [450, 300],
            "parameters": {
                "url": "http://backend:8000/api/products/pending-video",
                "method": "GET",
                "queryParameters": {
                    "parameter": [{"name": "limit", "value": "2"}]
                }
            }
        },
        {
            "name": "Telegram Notification",
            "type": "n8n-nodes-base.telegram",
            "position": [850, 300],
            "parameters": {
                "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
                "text": "🎬 Video pipeline started for {{ $json.name }}"
            }
        }
    ],
    "connections": {
        "Cron Trigger": {"main": [["Get Pending Products"]]},
        "Get Pending Products": {"main": [["Telegram Notification"]]}
    }
}
