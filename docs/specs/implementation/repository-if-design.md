# L4 — Repository IF Design (データベース設計)

> **SSoT**: Table definitions, Repository interfaces, data integrity.
> Tham chiếu: [capabilities.md §データ](../requirements/capabilities.md), [container-diagram.d2](../architecture/container-diagram.d2)

---

## 1. Design Principles

1. **Single DB** — PostgreSQL duy nhất cho toàn bộ system (MVP simplicity)
2. **Cap owns tables** — Mỗi cap sở hữu bảng riêng, cross-cap access qua FK hoặc event
3. **Soft delete** — Không xoá vật lý (trừ temp data). Dùng `status` field
4. **Timestamps** — Mọi bảng có `created_at`, `updated_at`
5. **UUID primary keys** — Tránh sequential ID leak

---

## 2. Table Definitions

### CAP-01: shopee-sync

```sql
CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shopee_item_id  VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(500) NOT NULL,
    price           INTEGER NOT NULL,              -- VND
    original_price  INTEGER,                       -- VND (nếu có giảm giá)
    category        VARCHAR(100) NOT NULL,
    description     TEXT,
    image_urls      JSONB NOT NULL DEFAULT '[]',   -- Array of URLs
    commission_rate DECIMAL(5,2) NOT NULL,          -- % (e.g., 12.50)
    affiliate_link  VARCHAR(1000) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',  -- active|inactive|out_of_stock
    priority_score  DECIMAL(5,4) DEFAULT 0,        -- 0.0000 - 1.0000
    last_synced_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_priority ON products(priority_score DESC) WHERE status = 'active';
CREATE INDEX idx_products_category ON products(category);
```

### CAP-02: script-gen

```sql
CREATE TABLE prompt_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    content_type    VARCHAR(50) NOT NULL,           -- product_review|lifestyle_tip|comparison|trending
    system_prompt   TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    variables       JSONB NOT NULL DEFAULT '[]',
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE scripts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID NOT NULL REFERENCES products(id),
    prompt_template_id  UUID NOT NULL REFERENCES prompt_templates(id),
    content_type        VARCHAR(50) NOT NULL,
    hook                VARCHAR(200) NOT NULL,
    body                TEXT NOT NULL,
    cta                 VARCHAR(200) NOT NULL,
    full_script         TEXT NOT NULL,
    estimated_duration_sec INTEGER NOT NULL,
    llm_provider        VARCHAR(20) NOT NULL,       -- groq|gemini|claude
    llm_model           VARCHAR(100) NOT NULL,
    generation_cost_usd DECIMAL(10,6) DEFAULT 0,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft|approved|rejected|used
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scripts_product ON scripts(product_id);
CREATE INDEX idx_scripts_status ON scripts(status);
```

### CAP-03: video-render

```sql
CREATE TABLE video_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id       UUID NOT NULL REFERENCES scripts(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued|rendering|done|failed
    output_path     VARCHAR(500),
    duration_sec    DECIMAL(5,1),
    file_size_mb    DECIMAL(6,2),
    resolution      VARCHAR(20) DEFAULT '1080x1920',
    tts_provider    VARCHAR(20) NOT NULL DEFAULT 'edge-tts',
    tts_voice       VARCHAR(50) NOT NULL DEFAULT 'vi-VN-HoaiMyNeural',
    background_type VARCHAR(30) NOT NULL DEFAULT 'product_images',
    has_music       BOOLEAN NOT NULL DEFAULT true,
    render_time_sec DECIMAL(6,1),
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_video_jobs_status ON video_jobs(status);
CREATE INDEX idx_video_jobs_product ON video_jobs(product_id);
```

### CAP-04: tiktok-publish

```sql
CREATE TABLE tiktok_auth (
    account_id      VARCHAR(100) PRIMARY KEY,
    access_token    TEXT NOT NULL,                  -- encrypted at rest
    refresh_token   TEXT NOT NULL,                  -- encrypted at rest
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    scopes          JSONB NOT NULL DEFAULT '[]',
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE publish_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_job_id    UUID NOT NULL REFERENCES video_jobs(id),
    tiktok_post_id  VARCHAR(100),
    title           VARCHAR(150) NOT NULL,
    description     TEXT NOT NULL,
    hashtags        JSONB NOT NULL DEFAULT '[]',
    scheduled_at    TIMESTAMP WITH TIME ZONE,
    published_at    TIMESTAMP WITH TIME ZONE,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending|uploading|published|failed|rejected
    tiktok_error    TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_publish_jobs_status ON publish_jobs(status);
CREATE INDEX idx_publish_jobs_scheduled ON publish_jobs(scheduled_at) WHERE status = 'pending';
```

### CAP-05: analytics

```sql
CREATE TABLE video_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publish_job_id  UUID NOT NULL REFERENCES publish_jobs(id),
    product_id      UUID NOT NULL REFERENCES products(id),
    tiktok_post_id  VARCHAR(100) NOT NULL,
    date            DATE NOT NULL,
    views           INTEGER NOT NULL DEFAULT 0,
    likes           INTEGER NOT NULL DEFAULT 0,
    comments        INTEGER NOT NULL DEFAULT 0,
    shares          INTEGER NOT NULL DEFAULT 0,
    clicks          INTEGER DEFAULT 0,
    conversions     INTEGER DEFAULT 0,
    revenue_vnd     INTEGER DEFAULT 0,
    ctr_pct         DECIMAL(5,2),
    engagement_rate DECIMAL(5,2),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(publish_job_id, date)
);

CREATE INDEX idx_metrics_date ON video_metrics(date DESC);
CREATE INDEX idx_metrics_product ON video_metrics(product_id);

CREATE TABLE daily_reports (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date                    DATE NOT NULL UNIQUE,
    total_videos_published  INTEGER NOT NULL DEFAULT 0,
    total_views             INTEGER NOT NULL DEFAULT 0,
    total_revenue_vnd       INTEGER NOT NULL DEFAULT 0,
    top_video_id            UUID REFERENCES publish_jobs(id),
    pipeline_health         VARCHAR(20) NOT NULL DEFAULT 'healthy',
    report_sent_at          TIMESTAMP WITH TIME ZONE,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### CAP-06: n8n-orchestration

```sql
CREATE TABLE workflow_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name   VARCHAR(100) NOT NULL,
    trigger_type    VARCHAR(20) NOT NULL,           -- cron|event|manual
    started_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at    TIMESTAMP WITH TIME ZONE,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',  -- running|success|partial_fail|failed
    caps_executed   JSONB NOT NULL DEFAULT '[]',
    error_log       TEXT,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE dead_letter_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_cap      VARCHAR(50) NOT NULL,
    job_id          UUID NOT NULL,
    job_type        VARCHAR(50) NOT NULL,           -- render|publish|sync|generate
    error_message   TEXT NOT NULL,
    attempts        INTEGER NOT NULL,
    first_failed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_failed_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at     TIMESTAMP WITH TIME ZONE,
    resolved_by     VARCHAR(50),                    -- auto|admin
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dlq_unresolved ON dead_letter_queue(source_cap) WHERE resolved_at IS NULL;
```

---

## 3. Repository Interfaces

```python
# Base repository pattern
class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None: ...
    @abstractmethod
    async def create(self, entity: T) -> T: ...
    @abstractmethod
    async def update(self, entity: T) -> T: ...

class ProductRepository(BaseRepository[Product]):
    async def get_active_by_priority(self, limit: int) -> list[Product]: ...
    async def get_by_shopee_id(self, shopee_item_id: str) -> Product | None: ...
    async def bulk_upsert(self, products: list[Product]) -> int: ...
    async def deactivate_missing(self, active_ids: set[str]) -> int: ...

class ScriptRepository(BaseRepository[Script]):
    async def get_pending_for_product(self, product_id: UUID) -> list[Script]: ...
    async def get_unused_approved(self, limit: int) -> list[Script]: ...

class VideoJobRepository(BaseRepository[VideoJob]):
    async def get_queued(self, limit: int) -> list[VideoJob]: ...
    async def get_failed_retryable(self) -> list[VideoJob]: ...

class PublishJobRepository(BaseRepository[PublishJob]):
    async def get_next_scheduled(self) -> PublishJob | None: ...
    async def get_pending_in_window(self, start: datetime, end: datetime) -> list[PublishJob]: ...

class VideoMetricRepository:
    async def upsert_daily(self, metric: VideoMetric) -> None: ...
    async def get_by_date_range(self, start: date, end: date) -> list[VideoMetric]: ...
    async def get_top_videos(self, days: int, limit: int) -> list[VideoMetric]: ...

class DLQRepository:
    async def add(self, entry: DLQEntry) -> None: ...
    async def get_unresolved(self) -> list[DLQEntry]: ...
    async def resolve(self, id: UUID, resolved_by: str) -> None: ...
```

---

## 4. Data Integrity Rules

| Rule | Implementation |
|------|---------------|
| Product cannot be deleted if has scripts | FK constraint + soft delete |
| Script cannot be deleted if has video_job | FK constraint |
| VideoJob cannot be deleted if has publish_job | FK constraint |
| Commission rate must be ≥ 0 | CHECK constraint |
| Priority score must be 0-1 | CHECK constraint |
| Publish scheduled_at must be future | Application-level validation |
| No duplicate metrics per video per day | UNIQUE(publish_job_id, date) |
| DLQ entries auto-expire after 30 days | Cron cleanup job |
