# L4 — Security & Observability Design

> **SSoT**: STRIDE mitigations, secret management, logging, monitoring, alerting.
> Tham chiếu: [container-diagram.d2](../architecture/container-diagram.d2), [infrastructure-design.md](infrastructure-design.md)

---

## 1. Threat Model (STRIDE)

| Threat | Category | Asset | Mitigation | Priority |
|--------|----------|-------|-----------|----------|
| T1 | Spoofing | TikTok OAuth tokens | Encrypt at rest, auto-refresh, never log tokens | P0 |
| T2 | Spoofing | Shopee API keys | .env file (gitignored), 600 permissions | P0 |
| T3 | Tampering | Product data in DB | Input validation at API layer, parameterized queries | P1 |
| T4 | Repudiation | Video publish actions | Structured logging with timestamps + job IDs | P2 |
| T5 | Info Disclosure | API keys in logs | Log sanitizer: mask any string matching key patterns | P0 |
| T6 | Info Disclosure | DB credentials | Docker secrets / .env, not in code/config committed | P0 |
| T7 | DoS | Celery queue flooding | Max queue size = 50, reject beyond | P1 |
| T8 | DoS | External API rate limits | Per-provider rate limiters, backoff | P1 |
| T9 | Elevation | N8N admin access | Basic auth + localhost only binding | P1 |
| T10 | Tampering | N8N workflows | Volume backup, no public exposure | P2 |

---

## 2. Secret Management

### Policy

| Rule | Implementation |
|------|---------------|
| No secrets in code | `.env` file, gitignored |
| No secrets in logs | Log sanitizer strips patterns: `sk-*`, `gsk_*`, `Bearer *` |
| No secrets in Docker image | Multi-stage build, .env mount at runtime |
| Token rotation | TikTok: auto-refresh every 12h. Others: manual rotate quarterly |
| Access control | .env file permission 600, owned by deploy user |

### Secret Inventory

| Secret | Location | Rotation |
|--------|----------|----------|
| DB_PASSWORD | .env | Manual, quarterly |
| SHOPEE_API_KEY | .env | Manual, on compromise |
| SHOPEE_API_SECRET | .env | Manual |
| TIKTOK_CLIENT_SECRET | .env | Manual |
| TIKTOK_ACCESS_TOKEN | DB (encrypted) | Auto every 12h |
| TIKTOK_REFRESH_TOKEN | DB (encrypted) | Auto when access refreshed |
| GROQ_API_KEY | .env | Manual |
| GEMINI_API_KEY | .env | Manual |
| TELEGRAM_BOT_TOKEN | .env | Manual |
| N8N_PASSWORD | .env | Manual |

---

## 3. Input Validation

### API Layer (FastAPI)

```python
# All inputs validated via Pydantic schemas
class SyncRequest(BaseModel):
    store_id: str = Field(max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    force: bool = False

class GenerateRequest(BaseModel):
    product_id: UUID
    content_type: Literal["product_review", "lifestyle_tip", "comparison", "trending"]

class PublishRequest(BaseModel):
    video_job_id: UUID
    scheduled_at: datetime | None = None  # Must be future if provided
```

### Database Layer

- All queries via SQLAlchemy ORM (parameterized, no raw SQL injection)
- UUID primary keys (not sequential, prevents enumeration)
- CHECK constraints on enums and ranges

---

## 4. Logging Design

### Format

```json
{
  "timestamp": "2026-06-24T08:30:00.123Z",
  "level": "INFO",
  "service": "backend",
  "cap": "script-gen",
  "job_id": "uuid-here",
  "message": "Script generated successfully",
  "duration_ms": 2340,
  "extra": {}
}
```

### Levels

| Level | Usage |
|-------|-------|
| DEBUG | Detailed trace (dev only) |
| INFO | Normal operations: job start/complete, sync results |
| WARNING | Recoverable issues: retry triggered, rate limit hit |
| ERROR | Failed operations: job failed, API error |
| CRITICAL | System-level: DB unreachable, all LLMs down |

### Log Rotation

```yaml
# logrotate config
storage/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## 5. Monitoring & Alerting

### Health Checks

| Check | Frequency | Alert if |
|-------|-----------|----------|
| Backend /health | 5 min | HTTP != 200 for 2 consecutive |
| PostgreSQL connection | 5 min | Connection refused |
| Redis connection | 5 min | Connection refused |
| Celery queue length | 10 min | Queue > 20 items |
| N8N /healthz | 10 min | HTTP != 200 |
| Storage disk usage | 1 hour | > 80% |

### Alert Channels

| Severity | Channel | Response time |
|----------|---------|---------------|
| CRITICAL | Telegram (immediate) | < 15 min |
| ERROR | Telegram (batched 5 min) | < 1 hour |
| WARNING | Daily report only | Next day review |

### Key Metrics (Tracked)

| Metric | Source | Dashboard |
|--------|--------|-----------|
| Videos published today | publish_jobs table | Overview page |
| Pipeline success rate | workflow_runs table | Overview page |
| DLQ count | dead_letter_queue table | Overview page (alert if > 0) |
| Total views (24h) | video_metrics table | Analytics page |
| Revenue (7d rolling) | video_metrics.revenue_vnd | Analytics page |
| API costs (monthly) | scripts.generation_cost_usd | Analytics page |
| Storage usage (GB) | `du -sh storage/videos/` | Overview page |

---

## 6. Network Security

### Port Exposure

| Service | Bind | Access |
|---------|------|--------|
| FastAPI (8000) | 0.0.0.0 | LAN only (no public internet) |
| N8N (5678) | 127.0.0.1 | Localhost only |
| PostgreSQL (5432) | 127.0.0.1 | Localhost only |
| Redis (6379) | 127.0.0.1 | Localhost only |
| Streamlit (8501) | 0.0.0.0 | LAN only |

### Firewall Rules (macOS)

```bash
# Block external access to internal services (if needed)
# Default: macOS firewall blocks incoming connections
# Docker: bind to 127.0.0.1 for sensitive services
```

---

## 7. Data Privacy

| Data | Classification | Retention | Access |
|------|---------------|-----------|--------|
| Product data (Shopee) | Public (from Shopee) | Indefinite | All caps |
| TikTok post metrics | Semi-public | 90 days raw, aggregated permanent | analytics cap |
| API credentials | Secret | Until rotated | Backend service only |
| Video files | Internal | 30 days | video-render, tiktok-publish |
| User (operator) data | N/A | N/A | Solo operator, no user data collected |

> **GDPR/Privacy**: Hệ thống không thu thập dữ liệu người dùng cuối (viewers). Chỉ có operator data = chính mình.
