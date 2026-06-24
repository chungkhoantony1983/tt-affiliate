# L4 — Directory Structure (ディレクトリ構造)

> **SSoT**: Cấu trúc thư mục vật lý cho backend + infrastructure.
> Tham chiếu: [component-landscape.d2](../architecture/component-landscape.d2), [container-diagram.d2](../architecture/container-diagram.d2)

---

## Backend (FastAPI)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry, routers mount
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Settings (pydantic-settings, .env)
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   └── events.py                # Event bus (simple pub/sub)
│   │
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── product.py               # Product, AffiliateLink
│   │   ├── script.py                # Script, PromptTemplate
│   │   ├── video_job.py             # VideoJob
│   │   ├── publish_job.py           # PublishJob, TikTokAuth
│   │   ├── analytics.py             # VideoMetric, DailyReport
│   │   └── orchestration.py         # WorkflowRun, DeadLetterQueue
│   │
│   ├── schemas/                     # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── product.py
│   │   ├── script.py
│   │   ├── video.py
│   │   ├── publish.py
│   │   └── analytics.py
│   │
│   ├── api/                         # FastAPI routers (1 per cap)
│   │   ├── __init__.py
│   │   ├── sync.py                  # POST /api/sync
│   │   ├── generate.py              # POST /api/generate
│   │   ├── render.py                # POST /api/render, GET /api/render/{id}
│   │   ├── publish.py               # POST /api/publish/next
│   │   └── analytics.py             # GET /api/analytics/*, POST /api/analytics/report
│   │
│   ├── services/                    # Business logic (1 dir per cap)
│   │   ├── __init__.py
│   │   ├── shopee/                  # CAP-01: shopee-sync
│   │   │   ├── __init__.py
│   │   │   ├── sync_orchestrator.py
│   │   │   ├── change_detector.py
│   │   │   ├── priority_calculator.py
│   │   │   └── adapters/
│   │   │       ├── __init__.py
│   │   │       ├── base.py          # PlatformSyncAdapter ABC
│   │   │       └── shopee_affiliate.py
│   │   │
│   │   ├── ai/                      # CAP-02: script-gen
│   │   │   ├── __init__.py
│   │   │   ├── script_generator.py
│   │   │   ├── template_loader.py
│   │   │   ├── quality_checker.py
│   │   │   └── adapters/
│   │   │       ├── __init__.py
│   │   │       ├── base.py          # LLMAdapter ABC
│   │   │       ├── groq_adapter.py
│   │   │       ├── gemini_adapter.py
│   │   │       └── claude_adapter.py
│   │   │
│   │   ├── video/                   # CAP-03: video-render
│   │   │   ├── __init__.py
│   │   │   ├── renderer.py
│   │   │   ├── tts_engine.py        # TTSEngine ABC + EdgeTTS impl
│   │   │   ├── ffmpeg_composer.py
│   │   │   ├── asset_manager.py
│   │   │   └── storage_manager.py
│   │   │
│   │   ├── tiktok/                  # CAP-04: tiktok-publish
│   │   │   ├── __init__.py
│   │   │   ├── publish_orchestrator.py
│   │   │   ├── schedule_manager.py
│   │   │   ├── auth_manager.py
│   │   │   └── adapters/
│   │   │       ├── __init__.py
│   │   │       ├── base.py          # PlatformPublishAdapter ABC
│   │   │       └── tiktok_v2.py
│   │   │
│   │   └── analytics/               # CAP-05: analytics
│   │       ├── __init__.py
│   │       ├── analytics_engine.py
│   │       ├── metric_fetcher.py
│   │       ├── report_generator.py
│   │       ├── alert_manager.py
│   │       ├── telegram_notifier.py
│   │       └── dashboard_exporter.py
│   │
│   └── tasks/                       # Celery async tasks
│       ├── __init__.py
│       └── video_tasks.py           # render_video_task
│
├── config/                          # External configs (YAML)
│   ├── llm-providers.yaml
│   ├── content-templates/
│   │   ├── product_review.yaml
│   │   ├── lifestyle_tip.yaml
│   │   └── comparison.yaml
│   ├── video-render.yaml
│   ├── tiktok-publish.yaml
│   └── analytics.yaml
│
├── migrations/                      # Alembic DB migrations
│   ├── env.py
│   └── versions/
│
├── tests/                           # Tests mirror services/ structure
│   ├── conftest.py
│   ├── test_shopee/
│   ├── test_ai/
│   ├── test_video/
│   ├── test_tiktok/
│   └── test_analytics/
│
├── requirements.txt
├── Dockerfile
└── pyproject.toml
```

---

## N8N Workflows

```
n8n/
├── workflows/
│   ├── W1-daily-full-pipeline.json
│   ├── W2-shopee-sync-only.json
│   ├── W3-publish-queue.json
│   ├── W4-daily-analytics.json
│   └── W5-error-recovery.json
├── credentials/
│   └── README.md                    # Setup instructions (no secrets)
└── README.md
```

---

## Dashboard (Streamlit)

```
dashboard/
├── app.py                           # Main entry: st.set_page_config + navigation
├── pages/
│   ├── overview.py                  # Pipeline health, today's stats
│   ├── products.py                  # Product list, priority, status
│   ├── videos.py                    # Video jobs, render status
│   └── analytics.py                 # Charts, revenue, top videos
├── components/
│   └── charts.py                    # Shared chart components
├── requirements.txt
└── Dockerfile
```

---

## Infrastructure

```
docker/
├── docker-compose.yml               # All services orchestration
├── .env.example                     # Template for environment vars
├── postgres/
│   └── init.sql                     # Initial schema (optional, prefer migrations)
└── nginx/                           # (future) reverse proxy
    └── nginx.conf

storage/                             # Runtime data (gitignored)
├── videos/                          # Rendered videos
├── assets/
│   ├── backgrounds/                 # Stock background images/videos
│   ├── music/                       # Royalty-free music
│   └── fonts/                       # Text overlay fonts
├── temp/                            # Working files during render
└── logs/                            # Application logs
```

---

## Root Level

```
tiktok_affiliate/                    # Project root
├── .github/
│   └── prompts/                     # VS Code Copilot slash commands
├── .claude -> agent/                # Symlink for Claude Code CLI
├── agent/                           # AI agent tooling (NOT design specs)
├── backend/                         # FastAPI + Celery (L5 code)
├── dashboard/                       # Streamlit UI
├── docker/                          # Docker Compose infrastructure
├── docs/                            # All design documents (L1-L4)
│   ├── manual/                      # Framework guides
│   ├── specs/                       # Project specs (strategy→impl)
│   ├── decision-records/            # DRs
│   └── operations/                  # Ops guides
├── n8n/                             # N8N workflow definitions
├── storage/                         # Runtime data (gitignored)
├── scripts/                         # Utility scripts
├── .env.example
├── .gitignore
└── FEASIBILITY.md
```
