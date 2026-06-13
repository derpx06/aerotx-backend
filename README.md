# AeroTx — AI Transaction Intelligence Platform

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-dc382d?style=flat-square&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-37814a?style=flat-square)
![AWS Bedrock](https://img.shields.io/badge/Amazon%20Bedrock-LLM-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-AWS-7B42BC?style=flat-square&logo=terraform&logoColor=white)

**Production-grade modular monolith for AI-powered financial transaction processing.**

Upload a CSV → deterministic cleaning → risk detection → Amazon Bedrock LLM classification → real-time analytics dashboard.

[Live Demo](https://alemeno-assignment.derpx06.online) &nbsp;·&nbsp; [API Docs](http://localhost:8000/docs) &nbsp;·&nbsp; [Worker Dashboard](http://localhost:5555)

</div>

---

## What It Does

AeroTx processes raw financial transaction CSV files through a fully automated, multi-stage pipeline:

1. **Upload** — chunked multipart file upload, SHA-256 deduplication, async queue dispatch
2. **Validate** — schema presence checks, file integrity verification
3. **Clean** — blank merchant resolution, decimal normalization, corrupt character stripping, currency alignment
4. **Risk Score** — four independent detectors score each transaction; signals are persisted per-transaction
5. **LLM Classify** — Amazon Bedrock batches transactions for merchant categorization and summary narrative generation
6. **Report** — SQL aggregates produce spend breakdowns, top merchants, and anomaly ratios
7. **Serve** — REST API + React dashboard with full pagination, filtering, timeline, and analytics

---

## Architecture

```mermaid
flowchart TD
    Browser["⚛️ React Frontend\nVite · TypeScript · CSS Modules"]

    subgraph Delivery ["Delivery Layer"]
        API["🚀 FastAPI\nport 8000"]
        Flower["🌸 Flower\nport 5555"]
    end

    subgraph Workers ["Celery Workers"]
        direction TB
        PW["⚙️ processing_worker\nprocessing_queue"]
        LW["🤖 llm_worker\nllm_queue"]
        RW["📊 reporting_worker\nreporting_queue"]
    end

    subgraph Storage ["Persistence"]
        DB[("🐘 PostgreSQL 16")]
        Redis[("⚡ Redis 7\nbroker + cache")]
        Files["📁 S3 / Local Volume\nCSV uploads"]
    end

    Bedrock["☁️ Amazon Bedrock\nnova-micro / claude-haiku"]

    Browser -->|REST + JSON| API
    API -->|enqueue processing_queue| Redis
    API --> DB
    API --> Files

    Redis --> PW
    PW --> DB
    PW --> Files
    PW -->|enqueue llm_queue| Redis

    Redis --> LW
    LW -->|converse API| Bedrock
    LW --> DB
    LW -->|enqueue reporting_queue| Redis

    Redis --> RW
    RW --> DB

    Flower -->|inspect| Redis
```

### Code Structure

```
backend/app/
├── api/              # FastAPI route handlers (jobs, health, metrics)
├── core/             # Config, database session, Celery app, logging
├── domain/           # Pure domain events — JobCreated, RiskAnalysisCompleted, etc.
├── ports/            # Interfaces — StorageProvider, LLMPort, DomainEventPublisher
├── infrastructure/   # Adapters — S3/Local storage, circuit breaker, event publisher
├── models/           # SQLAlchemy ORM models
├── repositories/     # Async data access — job, transaction, summary, event repos
├── schemas/          # Pydantic request/response schemas
├── services/
│   ├── cleaning/     # TransactionCleaner — streaming CSV parser + normalizer
│   ├── job/          # Pipeline orchestrator (stages.py) + coordinator (pipeline.py)
│   ├── llm/          # Bedrock client, classification service, summary service
│   ├── risk/         # RiskEngine + 4 detector strategies
│   ├── reporting/    # ReportingService — SQL aggregate computation
│   └── observability/# OpenTelemetry tracing, structured metrics
├── tasks/            # Celery task definitions — pipeline_tasks.py
└── utils/            # transaction_fingerprint for deduplication
```

> **Clean Architecture boundaries are strict.** Domain events, ports, and services contain zero imports from FastAPI, Celery, Redis, AWS, or SQLAlchemy. Those dependencies are wired in from the outside.

---

## Processing Pipeline

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant R as Redis
    participant P as processing_worker
    participant L as llm_worker
    participant W as reporting_worker
    participant B as Amazon Bedrock
    participant DB as PostgreSQL

    C->>A: POST /jobs/upload (multipart CSV)
    A->>A: SHA-256 checksum dedup check
    A->>DB: INSERT job (status=PENDING)
    A->>DB: publish JobCreated + FileUploaded events
    A->>R: enqueue → processing_queue
    A-->>C: 202 { job_id, status: PENDING }

    Note over P: processing_worker picks up task
    P->>DB: UPDATE job → PROCESSING
    P->>P: FileValidationStage — schema + file existence checks
    P->>P: CleaningStage — stream CSV, normalize, dedupe fingerprints
    P->>DB: bulk INSERT transactions
    P->>P: RiskStage — run 4 detectors, compute composite score
    P->>DB: bulk INSERT risk_signals
    P->>DB: UPDATE job → LLM_PROCESSING
    P->>R: enqueue → llm_queue

    Note over L: llm_worker picks up task
    L->>B: converse() — batch merchant classification
    B-->>L: JSON { categories }
    L->>DB: UPDATE transaction.category in bulk
    L->>B: converse() — narrative summary generation
    B-->>L: JSON { narrative, risk_level }
    L->>DB: UPDATE job → REPORTING
    L->>R: enqueue → reporting_queue

    Note over W: reporting_worker picks up task
    W->>DB: SQL aggregates — spend by category/currency, top merchants
    W->>DB: INSERT job_summary
    W->>DB: UPDATE job → COMPLETED

    C->>A: GET /jobs/{id}
    A->>DB: SELECT job + job_summary
    A-->>C: 200 { job, summary }
```

### Pipeline Stages (`services/job/stages.py`)

| Stage | Class | Output |
|-------|-------|--------|
| 1 | `FileValidationStage` | Validates file exists, resolves storage path |
| 2 | `CleaningStage` | Streams CSV, normalizes rows, writes `cleaning_result` to context |
| 3 | `PersistenceStage` | Bulk inserts transactions with SHA-256 fingerprints |
| 4 | `RiskStage` | Runs `RiskEngine`, bulk inserts `risk_signals` |
| 5 | `ClassificationStage` | Bedrock batch classify → update `transaction.category` |
| 6 | `SummaryStage` | Bedrock narrative → insert `job_summary` |
| 7 | `ReportingStage` | SQL aggregates → finalize `job_summary`, mark COMPLETED |

---

## Risk Engine

Located in `services/risk/`. Uses a **strategy pattern** — the `RiskEngine` coordinates four independent `RiskDetector` implementations:

| Detector | Signal Type | Score | Trigger |
|----------|------------|-------|---------|
| `MedianDetector` | `AMOUNT_OUTLIER` | 40 | Amount > 3× account median |
| `CurrencyDetector` | `CURRENCY_MISMATCH` | 30 | Domestic-looking merchant charged in USD |
| `DuplicateDetector` | `DUPLICATE_PATTERN` | 15 | Same date + merchant + amount + account_id |
| `NotesDetector` | `SUSPICIOUS_NOTE` | 20 | Notes contain: `urgent`, `wire`, `crypto`, `gift card`, `manual override` |
| `NotesDetector` | `MISSING_TXN_ID` | 10 | `txn_id` column is null or empty |

Composite risk score is the sum of all signals. Score thresholds map to `LOW / MEDIUM / HIGH` risk levels.

---

## Database Schema

```mermaid
erDiagram
    jobs ||--o{ transactions : "owns"
    jobs ||--o{ job_events : "emits"
    jobs ||--o| job_summaries : "summarizes"
    transactions ||--o{ risk_signals : "explains"

    jobs {
        uuid        id           PK
        string      filename
        string      storage_path
        string      status       "PENDING|PROCESSING|LLM_PROCESSING|REPORTING|COMPLETED|FAILED"
        string      file_checksum  "SHA-256 for dedup"
        int         row_count_raw
        int         row_count_clean
        bool        llm_failed
        string      error_message
        datetime    created_at
        datetime    started_at
        datetime    completed_at
    }

    transactions {
        uuid        id           PK
        uuid        job_id       FK
        string      txn_id       "nullable — source system ID"
        date        date
        string      merchant
        numeric     amount
        string      currency
        string      status
        string      category     "LLM-assigned"
        string      account_id
        bool        is_anomaly
        int         risk_score
        string      risk_level   "LOW|MEDIUM|HIGH"
        string      notes
        string      anomaly_reason
        string      fingerprint  "SHA-256 dedup key"
        datetime    created_at
    }

    risk_signals {
        uuid        id             PK
        uuid        transaction_id FK
        string      signal_type    "AMOUNT_OUTLIER|CURRENCY_MISMATCH|DUPLICATE_PATTERN|SUSPICIOUS_NOTE|MISSING_TXN_ID"
        float       signal_score
        string      description
    }

    job_events {
        uuid        id               PK
        uuid        job_id           FK
        string      event_type       "domain event class name"
        string      domain_event_name
        datetime    timestamp
        jsonb       metadata_
    }

    job_summaries {
        uuid        id                PK
        uuid        job_id            FK
        numeric     total_spend_inr
        numeric     total_spend_usd
        jsonb       top_merchants     "[{ merchant, total }]"
        jsonb       currency_breakdown "{ USD: 12400.0, INR: ... }"
        int         anomaly_count
        text        narrative         "Bedrock-generated"
        string      risk_level        "LOW|MEDIUM|HIGH"
    }
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- AWS account (optional — only needed for LLM classification)

### 1. Clone & configure

```bash
git clone https://github.com/derpx06/aerotx-backend.git
cd aerotx-backend
cp .env.example .env
# Fill in your values — see Environment Variables below
```

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React dashboard |
| API | http://localhost:8000 | FastAPI REST |
| OpenAPI | http://localhost:8000/docs | Interactive API docs |
| Flower | http://localhost:5555 | Celery worker monitoring |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Broker + cache |

Alembic migrations run automatically on container startup.

### 3. Upload a CSV

```bash
curl -F "file=@transactions.csv" http://localhost:8000/jobs/upload
# → { "id": "550e8400...", "status": "PENDING" }

curl http://localhost:8000/jobs/550e8400.../status
# → { "status": "COMPLETED", "summary": { ... } }
```

### CSV Format

**Required columns:**

```
date, merchant, amount, currency, status, account_id
```

**Optional columns:**

```
txn_id, category, notes
```

**Example:**

```csv
date,merchant,amount,currency,status,account_id,txn_id,notes
2024-01-15,Acme Corp,1250.00,USD,COMPLETED,ACC001,TXN001,
2024-01-16,,8900.00,HKD,COMPLETED,ACC002,,urgent payment
2024-01-17,AWS Cloud,412.50,USD,COMPLETED,ACC001,TXN003,
2024-01-17,AWS Cloud,412.50,USD,COMPLETED,ACC001,,
```

---

## Environment Variables

### Backend — `.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SYNC_DATABASE_URL` | ✅ | — | `postgresql+psycopg://user:pass@host:5432/db` — used by Alembic |
| `REDIS_URL` | ✅ | `redis://redis:6379/0` | Redis connection string |
| `UPLOAD_DIR` | ✅ | `/tmp/transaction-uploads` | Local path for CSV files (ignored if using S3) |
| `AWS_ACCESS_KEY_ID` | ⚠️ | — | AWS credentials for Bedrock. Omit when using an IAM role. |
| `AWS_SECRET_ACCESS_KEY` | ⚠️ | — | AWS secret. Omit when using an IAM role. |
| `AWS_REGION` | ⚠️ | `us-east-1` | AWS region where Bedrock model access is enabled |
| `BEDROCK_MODEL_ID` | ⚠️ | `amazon.nova-micro-v1:0` | Model to use for classification + narrative |
| `STORAGE_PROVIDER` | ❌ | `local` | `local` or `s3` |
| `S3_BUCKET_NAME` | ❌ | — | Required if `STORAGE_PROVIDER=s3` |
| `ENVIRONMENT` | ❌ | `local` | `local` · `staging` · `production` |
| `LOG_LEVEL` | ❌ | `INFO` | Python log level |
| `UPLOAD_MAX_BYTES` | ❌ | `104857600` | Max file size — 100 MB default |
| `CSV_BATCH_SIZE` | ❌ | `5000` | Rows per bulk insert batch |

> ⚠️ = Optional, but **LLM classification falls back to heuristics** if AWS credentials are absent. The pipeline still completes.

**Bedrock model options** — must be enabled under AWS Console → Amazon Bedrock → Model access:

| `BEDROCK_MODEL_ID` | Cost | Quality |
|--------------------|------|---------|
| `amazon.nova-micro-v1:0` | 💚 Lowest | Good — default |
| `amazon.nova-lite-v1:0` | 💛 Low | Better reasoning |
| `anthropic.claude-3-haiku-20240307-v1:0` | 🟠 Medium | Best — requires model access request |

### Frontend — `frontend/.env.local`

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_GOOGLE_CLIENT_ID` | ✅ | Google OAuth 2.0 Client ID |

**Getting a Google Client ID:**

1. [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials → Create OAuth client ID
2. Application type: **Web application**
3. Authorized JavaScript origins: `http://localhost:5173` + your production domain
4. Leave **Authorized redirect URIs** empty — the app uses the GSI callback flow, not server-side redirects
5. Copy the Client ID → paste into `frontend/.env.local`

---

## API Reference

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/jobs/upload` | Upload CSV. Returns `job_id` immediately (202). Idempotent — duplicate files return the existing job. |
| `GET` | `/jobs` | List jobs. Query: `?status=COMPLETED&limit=50&offset=0` |
| `GET` | `/jobs/{id}` | Job record with embedded `job_summary` |
| `GET` | `/jobs/{id}/status` | Lightweight status poll. Includes summary only when `COMPLETED`. |
| `GET` | `/jobs/{id}/results` | Paginated transactions + anomalies + category spend. Query: `?limit=100&offset=0` |
| `GET` | `/jobs/{id}/timeline` | Full ordered event log for the job |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/jobs/global/analytics` | Cross-job: category spend, currency breakdown, top merchants, risk counts, daily trend |
| `GET` | `/jobs/global/transactions` | Filtered global transaction explorer. Supports: `search`, `category`, `currency`, `risk_level`, `min_amount`, `max_amount`, `limit`, `offset` |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Full readiness: PostgreSQL + Redis + Celery workers + Bedrock connectivity |
| `GET` | `/health/live` | Liveness probe — always `200 { "status": "ok" }` |
| `GET` | `/metrics` | Operational metrics snapshot from `MetricsService` |
| `GET` | `/docs` | Swagger UI — interactive OpenAPI 3.1 documentation |

### Job Status Lifecycle

```
PENDING → PROCESSING → LLM_PROCESSING → REPORTING → COMPLETED
                   ↘                ↘             ↘
                   FAILED          FAILED         FAILED
```

`llm_failed=true` is set when Bedrock fails after all retries. The pipeline **continues** — heuristic categories are used and the job still reaches `COMPLETED`.

### Example Responses

**`POST /jobs/upload` → 202**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "q1_transactions.csv",
  "status": "PENDING"
}
```

**`GET /jobs/{id}` → 200**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "q1_transactions.csv",
  "status": "COMPLETED",
  "row_count_raw": 1500,
  "row_count_clean": 1487,
  "llm_failed": false,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:31:42Z",
  "summary": {
    "total_spend_usd": 48291.50,
    "total_spend_inr": 4021234.00,
    "anomaly_count": 23,
    "risk_level": "MEDIUM",
    "narrative": "Q1 batch shows elevated HKD activity from three unverified merchant IDs...",
    "top_merchants": [
      { "merchant": "AWS Cloud", "total": 12400.00 },
      { "merchant": "Acme Corp", "total": 8900.00 }
    ],
    "currency_breakdown": { "USD": 41200.00, "HKD": 7091.50 }
  }
}
```

---

## Frontend

Vite + React 19 + TypeScript SPA with CSS Modules. No external UI library.

### Views

| View | Description |
|------|-------------|
| Landing | Hero + Google Sign-In. Reads `VITE_GOOGLE_CLIENT_ID` from env — no runtime config input. |
| Dashboard | Job list, status badges, upload modal trigger |
| Job Detail | Summary card, paginated transaction table, risk signals, audit timeline |
| Transaction Explorer | Global cross-job table with search + filters (category, currency, risk level, amount range) |
| Analytics | Category spend charts, currency distribution, daily trend, top merchants |
| System Health | Live check for PostgreSQL, Redis, workers, Bedrock |

### Auth Flow

1. Google GSI SDK loaded dynamically on landing page
2. User clicks the Sign In button — Google returns a JWT credential in a browser callback (no redirect)
3. Frontend decodes JWT payload (base64) — extracts `name`, `email`, `picture`
4. User object persisted to `localStorage` → redirected to dashboard
5. No backend session or token storage — purely client-side

### Local Dev

```bash
cd frontend
npm install
echo "VITE_GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com" > .env.local
npm run dev            # → http://localhost:5173
```

### Deploy to Vercel

1. Import repo at vercel.com — set Root Directory to `frontend`
2. Add env var: `VITE_GOOGLE_CLIENT_ID`
3. Deploy
4. Add Vercel domain to Google OAuth → Authorized JavaScript Origins

---

## Engineering Notes

### LLM Resilience
- **Batched** — multiple transactions per API call to minimize cost and latency
- **Retried** — exponential backoff with jitter, up to 4 attempts
- **Circuit breaker** — 3 consecutive failures → circuit opens → heuristic fallback for 60 s → auto-recover
- **Validated** — structured JSON output validated inside the retry loop via `response_validator.py`
- **Non-blocking** — boto3 (synchronous) run via `asyncio.run_in_executor` to keep the event loop free
- **Graceful degradation** — `llm_failed=true` is set; pipeline reaches `COMPLETED` using heuristics

### Idempotency
- Upload deduplication: SHA-256 file checksum checked before creating a new job
- Transaction deduplication: SHA-256 fingerprint per row prevents duplicate inserts on task replay
- Event publisher uses stable idempotency keys
- Summary uses `INSERT ... ON CONFLICT DO UPDATE`

### Performance
- CSV is **streamed** — handles millions of rows without full memory load
- Transactions are **bulk-inserted** via `bulk_insert_mappings`
- SQL aggregates used for all reporting — no Python-side computation
- LLM classification only loads **uncategorized** rows
- Celery `prefetch_multiplier=1` for fair queue scheduling

### Storage Abstraction
`STORAGE_PROVIDER=local` → `LocalStorageProvider` (Docker volume)  
`STORAGE_PROVIDER=s3` → `S3StorageProvider` (async, non-blocking, presigned URL support)

Swap via env var — zero code changes required.

### Observability
OpenTelemetry auto-instruments FastAPI, HTTPX, Celery, and SQLAlchemy. All logs are structured JSON with request correlation IDs.

---

## Local Development (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/transactions"
export SYNC_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/transactions"
export REDIS_URL="redis://localhost:6379/0"

# API
uvicorn app.main:app --reload --port 8000

# Workers (separate terminals)
celery -A app.core.celery_app worker -Q processing_queue -c 2 --loglevel=info
celery -A app.core.celery_app worker -Q llm_queue -c 1 --loglevel=info
celery -A app.core.celery_app worker -Q reporting_queue -c 2 --loglevel=info

# Flower
celery -A app.core.celery_app flower --port=5555
```

```bash
# Tests
pytest
pytest --cov=app --cov-fail-under=80

# Lint
ruff check . && ruff format .
```

---

## Infrastructure (Terraform)

`terraform/` provisions the full AWS stack for production:

- **VPC** — multi-AZ with public + private subnets, NAT Gateway
- **ECS Fargate** — separate task definitions for API, processing_worker, llm_worker, reporting_worker (independent scaling)
- **RDS PostgreSQL** — Multi-AZ with automated backups
- **ElastiCache Redis** — cluster mode
- **ALB** — HTTPS termination, health check routing
- **S3** — CSV upload storage with lifecycle policies
- **IAM** — least-privilege task roles with Bedrock `invoke_model` permission
- **Security Groups** — layered ingress rules per service

```bash
cd terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply
```

---

## Scaling

| Traffic | Action |
|---------|--------|
| **10x** | `docker compose up --scale processing_worker=4 --scale llm_worker=2` |
| **100x** | Switch to `STORAGE_PROVIDER=s3`, add Postgres read replicas, PgBouncer, Redis Cluster |
| **1000x** | Separate `llm_worker` into dedicated LLM microservice, add SQS/Kafka event streaming, move analytics to OLAP (Redshift / ClickHouse) |

Clean Architecture port boundaries make all these migrations incremental — no re-architecture needed.
