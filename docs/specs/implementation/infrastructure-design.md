# L4 — Infrastructure Design (インフラ設計)

> **SSoT**: Deploy, environment, scaling, DB ops, disaster recovery.
> Tham chiếu: [container-diagram.d2](../architecture/container-diagram.d2)

---

## 1. Deployment Architecture

### Stack

| Service | Technology | Deploy | Port |
|---------|-----------|--------|------|
| FastAPI Backend | Python 3.12 + uvicorn | Docker container | 8000 |
| Celery Worker | Python 3.12 + celery | Docker container | — |
| N8N | Node.js (official image) | Docker container | 5678 |
| PostgreSQL | PostgreSQL 16 | Docker container | 5432 |
| Redis | Redis 7 | Docker container | 6379 |
| Streamlit | Python 3.12 + streamlit | Docker container | 8501 |

### Docker Compose

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tiktok_affiliate
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  backend:
    build: ../backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    volumes:
      - ../storage:/app/storage

  celery_worker:
    build: ../backend
    command: celery -A app.tasks worker --loglevel=info --concurrency=2
    env_file: .env
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    volumes:
      - ../storage:/app/storage

  n8n:
    image: n8nio/n8n:latest
    environment:
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: ${N8N_USER}
      N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD}
      WEBHOOK_URL: http://localhost:5678/
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - backend

  dashboard:
    build: ../dashboard
    env_file: .env
    ports:
      - "8501:8501"
    depends_on:
      postgres: { condition: service_healthy }

volumes:
  postgres_data:
  n8n_data:
```

---

## 2. Environment Management

### Environments

| Env | Mô tả | Database | N8N |
|-----|--------|----------|-----|
| **development** | Local dev (IDE) | SQLite hoặc local Postgres | Manual trigger only |
| **production** | Docker Compose trên desktop | PostgreSQL container | Full cron schedules |

> Note: Không có staging/CI — solo project, single machine.

### Environment Variables (.env)

```bash
# Database
DB_USER=affiliate_user
DB_PASSWORD=<generated>
DB_HOST=postgres
DB_PORT=5432
DB_NAME=tiktok_affiliate

# Redis
REDIS_URL=redis://redis:6379/0

# Shopee
SHOPEE_STORE_ID=<your_store_id>
SHOPEE_API_KEY=<your_api_key>
SHOPEE_API_SECRET=<your_api_secret>

# TikTok
TIKTOK_CLIENT_KEY=<your_client_key>
TIKTOK_CLIENT_SECRET=<your_client_secret>
TIKTOK_ACCOUNT_ID=<your_account_id>

# LLM
GROQ_API_KEY=<your_key>
GEMINI_API_KEY=<your_key>

# Telegram
TELEGRAM_BOT_TOKEN=<your_token>
TELEGRAM_CHAT_ID=<your_chat_id>

# N8N
N8N_USER=admin
N8N_PASSWORD=<generated>

# App
APP_ENV=production
LOG_LEVEL=INFO
STORAGE_DIR=/app/storage
```

---

## 3. Startup & Shutdown

### Startup Sequence

```
1. docker compose up -d postgres redis
2. Wait for healthchecks (pg_isready, redis-cli ping)
3. docker compose up -d backend
4. Backend runs Alembic migrations on startup
5. docker compose up -d celery_worker n8n dashboard
6. N8N loads workflows from volume
7. Pipeline ready
```

### Shutdown (graceful)

```
1. docker compose stop n8n          # Stop scheduling new jobs
2. Wait for active Celery tasks to complete (max 5 min)
3. docker compose stop celery_worker backend
4. docker compose stop dashboard
5. docker compose stop postgres redis
```

### Auto-restart on boot

```bash
# /etc/systemd/system/tiktok-affiliate.service (Linux)
# OR: Login Items on macOS
# Simplest: crontab @reboot
@reboot cd /path/to/docker && docker compose up -d
```

---

## 4. Database Operations

### Migrations

```bash
# Create migration
cd backend && alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Backup Strategy

| What | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| PostgreSQL full dump | Daily 02:00 AM | 7 days | `pg_dump` → `storage/backups/` |
| N8N data volume | Weekly | 4 weeks | `docker cp` |
| Config files | On change | Git tracked | Commit to repo |
| Storage/videos | No backup | 30 days retention | Auto-delete old videos |

```bash
# Backup script (cron daily 02:00)
#!/bin/bash
BACKUP_DIR="storage/backups"
DATE=$(date +%Y%m%d)
docker compose exec -T postgres pg_dump -U $DB_USER $DB_NAME > "$BACKUP_DIR/db_$DATE.sql"
find "$BACKUP_DIR" -name "db_*.sql" -mtime +7 -delete
```

### Storage Cleanup

```bash
# Auto-delete videos older than 30 days (cron daily 03:00)
find storage/videos/ -name "*.mp4" -mtime +30 -delete
find storage/temp/ -mtime +1 -delete
```

---

## 5. Monitoring & Health

### Health Endpoints

| Service | Endpoint | Expected |
|---------|----------|----------|
| Backend | `GET /health` | `{"status": "ok", "db": "connected", "redis": "connected"}` |
| N8N | `GET /healthz` | HTTP 200 |
| Dashboard | `GET /` (Streamlit) | HTTP 200 |

### Self-monitoring via N8N

- W5 (error-recovery) checks pipeline health every 30 min
- Telegram alert nếu: backend unreachable, DB connection failed, Celery queue backlog > 10

---

## 6. Scaling Notes (Future)

| Bottleneck | Solution | Trigger |
|-----------|----------|---------|
| Video render speed | Increase Celery concurrency (--concurrency=4) | > 20 videos/day |
| DB connections | Connection pooling (pgbouncer) | > 100 concurrent queries |
| Storage space | External NAS mount / S3-compatible | > 50GB |
| Multi-machine | Docker Swarm / separate workers | Revenue > $100/mo → justify server cost |
