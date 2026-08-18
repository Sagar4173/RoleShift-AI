# RoleShift AI

Role-level AI intelligence for the modern workforce — an enterprise application for the
**Modus Enterprise AI Build Challenge**.

**Selected assignment: Assignment 6 — Role-Level AI Intelligence**

The application analyzes the full role lifecycle:

```
Role → Processes → Activities → Current Skills
  → AI Exposure → Automated Activities → Augmented Activities
  → New Responsibilities → Future Skills → Skill Gaps
  → Recommendations → Reskilling Priority → Future Role Profile
```

Everything is structured, persisted, explainable, and dynamically computable for **any** new role —
including surprise roles introduced live during the demo. The AI pipeline is **fully implemented**
(not planned): arbitrary roles are analyzed against real business context through a versioned,
strictly validated AI pipeline with full provenance.

---

## Current status

- ✅ **Role-Level AI Intelligence shipped** — any role → AI exposure / automation / augmentation,
  per-activity impacts with human responsibilities, future responsibilities, future skills,
  deterministic skill-gap computation, recommendations, reasoning, reskilling priority.
- ✅ **Live production deployment** — Vercel (frontend) → Render (backend) → MongoDB Atlas → Ollama
  Cloud, verified end-to-end in the browser.
- ✅ **Provenance & auditability** — every analysis records provider, model, prompt version
  (content-hashed), input hash, and a full run lifecycle (`AnalysisRun`).
- ✅ **Deterministic post-processing** — AI output is validated against a strict schema, scores are
  clamped to [0,1], impact levels are derived from thresholds, and skill gaps are computed
  deterministically (invariant-tested).
- ✅ **Cost-aware** — identical analysis requests are deduplicated via input hashing; `force`
  re-analysis is available for deliberate reruns.
- ✅ **Authentication, RBAC & tenant isolation** — session-based auth (scrypt password hashing,
  hashed session tokens, HttpOnly/SameSite/Secure cookies), owner / admin / analyst / viewer roles
  enforced server-side (404-before-403), and organization-scoped data with a single workspace.
- ✅ **Rate limiting** — per-client token-bucket limits on authentication, analysis, and
  member-management endpoints, with `Retry-After` headers surfaced in the UI.
- ✅ **Testing** — 236 passing backend tests (arbitrary-role pipeline, context gate, malformed AI
  output, provider-failure handling, dedup/force, secret-leakage guards, production docs disabled,
  rate limiting, RBAC), strict TypeScript frontend, production deployment verified end-to-end.

Known limitations are listed at the bottom of this file.

## Architecture overview

```
React frontend (Vite + TS + Tailwind)
        │  HTTP /api/v1 (same-origin via Vercel rewrites)
        ▼
FastAPI backend (versioned API)
        │
        ▼
Service layer (business logic, analysis pipeline)
        │
        ├── AI provider abstraction (services/ai)
        │       └── Ollama Cloud (gpt-oss:120b) → structured JSON → strict schema validation
        ▼
Repository layer (MongoDB access)
        │
        ▼
MongoDB Atlas (Beanie ODM)
```

The AI provider is isolated behind a provider abstraction
(`backend/app/services/ai/base.py`) with a factory (`get_provider`). The configured provider is
**Ollama Cloud (`gpt-oss:120b`)**; DeepSeek and a `none`/no-op provider are also implemented and
selected purely via environment variables — no business logic touches a provider directly.

See [`docs/architecture.md`](docs/architecture.md) for the full design.

## Technology stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript (strict), Vite 6, Tailwind CSS 4, React Router |
| Backend | Python 3.13+ (3.14 on Render), FastAPI, Pydantic v2, Pydantic Settings |
| Database | MongoDB Atlas, Beanie ODM (Motor driver) |
| AI | Ollama Cloud (`gpt-oss:120b`); DeepSeek and no-op providers available via config |
| Production | Vercel (frontend), Render (backend) |
| Dev | Docker Compose (frontend, backend, MongoDB), pytest |

## Project structure

```
roleshift-ai/
├── frontend/                 # React + Vite + Tailwind
│   └── src/
│       ├── components/       # UI primitives
│       ├── pages/            # Dashboard, Role Intelligence, Comparison, New Role, Skills, Settings
│       ├── layouts/          # AppLayout (sidebar + header)
│       ├── services/         # Typed API client (no fetch scattered in components)
│       ├── hooks/            # useApi data-fetching hook
│       ├── types/            # TS types mirroring backend schemas
│       └── lib/
├── backend/                  # FastAPI + Beanie
│   ├── app/
│   │   ├── api/routes/       # /api/v1 endpoints
│   │   ├── core/             # config, logging, exceptions, database
│   │   ├── models/           # Beanie documents (incl. RoleAnalysis, AnalysisRun)
│   │   ├── schemas/          # Pydantic request/response validation
│   │   ├── repositories/     # data access layer
│   │   ├── services/ai/      # provider abstraction + DeepSeek/Ollama Cloud/no-op providers
│   │   └── main.py           # application factory
│   └── tests/
├── docker-compose.yml        # mongo + backend + frontend
├── render.yaml               # production backend config (Render Blueprint)
├── .env.example
└── docs/architecture.md
```

## Local setup

Prerequisites: Python 3.13+, Node 20+, and a MongoDB database — the recommended option is
**MongoDB Atlas** (free tier, fully managed, nothing installed locally).

### 1. MongoDB Atlas

1. Create a free cluster at <https://www.mongodb.com/atlas>.
2. Create a database user and allow network access from your IP.
3. Copy the connection string (e.g. `mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/`).

### 2. Environment variables

```bash
# from the project root
cp .env.example backend/.env
```

Then edit `backend/.env` and set your Atlas connection string:

```env
MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
MONGODB_DATABASE=roleshift
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

The backend reads `./.env` (or `../.env`) automatically. `.env` files are git-ignored —
**never commit real credentials**.

### 3. Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate            # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

- API base: `http://localhost:8000/api/v1`
- Interactive docs (Swagger UI): <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Health: <http://localhost:8000/health>, DB health: <http://localhost:8000/health/db>

To run the real AI pipeline locally, set `AI_PROVIDER=ollama_cloud`, `AI_MODEL=gpt-oss:120b`, and
`OLLAMA_API_KEY` in `backend/.env`. Without a provider, `AI_PROVIDER=none` returns a clear
"provider not configured" error instead of faking results.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` and `/health` to the backend on
port 8000 — no frontend env file is required (see `frontend/.env.example` for the optional
`VITE_API_BASE_URL` override).

### 5. Tests

```bash
cd backend
pytest
```

Tests run against an in-memory MongoDB (`mongomock-motor`) — no live database and no real AI calls.

## Running with Docker (optional)

Docker Compose is provided for completeness (frontend + backend + bundled MongoDB), but the
**recommended workflow is plain local development** with MongoDB Atlas as described above.

```bash
docker compose up --build
```

- Frontend: <http://localhost:8080>
- Backend API: <http://localhost:8000> — Swagger at <http://localhost:8000/docs>
- Bundled MongoDB: `localhost:27017` (data persisted in the `mongo-data` volume)

To use Atlas instead of the bundled MongoDB service, set `MONGODB_URL` and `MONGODB_DATABASE` in
the compose `environment` block of the `backend` service to your Atlas values.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | `development`, `staging`, `production`, `test` |
| `LOG_LEVEL` | `INFO` | Log level (`DEBUG`…`CRITICAL`) |
| `APP_DEBUG` | `false` | Debug mode flag |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DATABASE` | `roleshift` | Database name |
| `MONGODB_TIMEOUT_MS` | `5000` | DB server-selection timeout |
| `CORS_ORIGINS` | `http://localhost:5173,…` | Comma-separated allowed origins (no wildcard by default) |
| `API_V1_PREFIX` | `/api/v1` | API version prefix |
| `AI_PROVIDER` | `deepseek` | `deepseek`, `ollama_cloud`, or `none` |
| `AI_MODEL` | `deepseek-chat` | Model id passed to the provider |
| `AI_TIMEOUT_SECONDS` | `60` | Provider request timeout (10–300) |
| `AI_TEMPERATURE` | `0.3` | Provider sampling temperature (0.0–2.0) |
| `DEEPSEEK_API_KEY` | — | DeepSeek provider key (server-side secret) |
| `OLLAMA_API_KEY` | — | Ollama Cloud provider key (server-side secret) |

Frontend (optional): `VITE_API_BASE_URL` — backend base URL when not using the dev proxy.

## API documentation

- **Development/test:** Swagger UI at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json`.
- **Production: all three are disabled (404)** to reduce the public attack surface.
- Health probes: `/health` (liveness), `/health/db` (MongoDB connectivity).

### API endpoints (`/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | Create an account (joins the workspace as viewer) |
| POST | `/auth/login` | Sign in (session cookie) |
| POST | `/auth/logout` | Sign out |
| GET | `/auth/me` | Current session user |
| GET/POST | `/organizations` | List / create organizations |
| GET | `/organizations/{id}` | Fetch one organization |
| GET | `/organizations/members` | List organization members |
| PUT/DELETE | `/organizations/members/{user_id}` | Change member role / remove member |
| GET | `/roles` | List roles (paginated, with latest analysis) |
| POST | `/roles` | Create a role |
| POST | `/roles/analyze-new` | Create a role with context **and run its first analysis** |
| GET | `/roles/compare` | Role + latest-analysis pairs for comparison |
| GET | `/roles/{id}` | Fetch one role |
| PUT | `/roles/{id}/current-skills` | Replace a role's current skills |
| DELETE | `/roles/{id}` | Delete a role |
| GET | `/roles/{id}/analysis` | Latest persisted analysis for a role |
| POST | `/roles/{id}/analyze` | Run the AI analysis pipeline (with `force` support) |
| GET/POST | `/processes` | List / create processes |
| GET/POST | `/activities` | List / create activities |
| GET/POST | `/skills` | List / create skills |
| GET | `/dashboard/summary` | Workforce analytics summary |
| GET | `/dashboard/skills` | Future-skill demand aggregation |
| GET | `/health` | Liveness probe |
| GET | `/health/db` | Database readiness probe |

## AI pipeline

1. **Context gathering** — the role's own processes, activities, and current skills are loaded
   (role-scoped, never org-wide data).
2. **Data-quality gate** — roles without an industry, activities, or current skills are refused
   before any AI call (`_validate_context`).
3. **Prompt** — a versioned template (content hash → `PROMPT_VERSION`) with a strict JSON output
   schema.
4. **Provider call** — Ollama Cloud with `format: json` (structured output requested).
5. **Output validation** — the response is parsed (tolerant of markdown fences / surrounding
   prose) and validated against the strict `AIAnalysisResult` Pydantic schema (bounds, unknown
   fields rejected).
6. **Deterministic normalisation** — score clamping to [0,1], impact-level thresholds, skill-gap
   computation (future skill absent from current skills), temp-ref → real activity mapping.
7. **Persistence** — `RoleAnalysis` + `AnalysisRun` (status lifecycle, input hash, provider/model/
   prompt provenance).
8. **Dedup** — a completed run with an identical input hash short-circuits unless `force=true`.

No role is hard-coded anywhere: the same pipeline analyzes any role supplied through the API.

## Production deployment

The production architecture is **frozen**:

| Layer | Platform |
|-------|----------|
| Frontend | Vercel — <https://roleshiftai.vercel.app> |
| Backend | Render (Web Service) — <https://roleshift-ai.onrender.com> |
| Database | MongoDB Atlas |
| AI | Ollama Cloud (`ollama_cloud`, `gpt-oss:120b`) |

### Backend → Render

1. `render.yaml` is committed (Render Blueprint) — service `RoleShift-AI`, `rootDir: backend`,
   health check `/health`, start command `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`
   (binds `0.0.0.0`, uses Render's `$PORT`).
2. Secrets (`MONGODB_URL`, `OLLAMA_API_KEY`) live only in the Render dashboard **Environment**
   panel — never in `render.yaml`, never committed.
3. `CORS_ORIGINS` is set to the exact Vercel origin.
4. Production disables `/docs`, `/redoc`, and `/openapi.json`.

### Frontend → Vercel

1. Vercel project at repo root `frontend/` (framework preset: Vite, build `npm run build`,
   output `dist`).
2. `frontend/vercel.json` rewrites `/api/:path*` and `/health/:path*` to the Render backend and
   provides the SPA catch-all for `BrowserRouter` deep links (`/role-intelligence/<id>`,
   `/compare`, …).
3. The frontend API base is the relative `/api/v1` (`src/services/api.ts`), so no build-time
   environment variable is required.

### MongoDB Atlas

- Atlas connection string set as `MONGODB_URL` (server-side secret).
- The app never exposes connection details to clients; indexes are managed by Beanie with
  `allow_index_dropping=False`, so production indexes are never dropped.

### Ollama Cloud

- `AI_PROVIDER=ollama_cloud`, `AI_MODEL=gpt-oss:120b`, `OLLAMA_API_KEY` (server-side secret).
- The key is used only in the backend (`backend/app/services/ai/providers/ollama_cloud.py`),
  never sent to the browser and never logged. Malformed provider output is validated against the
  strict `AIAnalysisResult` schema before persistence.

### Secret handling

- `.env` files are git-ignored. Set real credentials only via the Render dashboard.
- Anything starting with `VITE_` is browser-visible — never put API keys or Mongo credentials in
  frontend env vars.
- `backend/.env`, logs, `node_modules`, `dist`, and virtual environments are git-ignored.

## Known limitations

- **Auth & RBAC are implemented; self-service multi-tenant signup is not** — session
  authentication, role-based access control (owner / admin / analyst / viewer, enforced
  server-side), and organization-scoped data are shipped. New accounts join the single default
  workspace as viewers; there is no per-tenant onboarding flow or tenant-scoped UI.
- **Rate limiting is per-instance** — token-bucket limits on auth, analysis, and member-management
  endpoints are enforced per process with `Retry-After` headers; there is no distributed limiter,
  so a multi-instance deployment would divide the limits across instances.
- **No multilingual support** — UI strings and prompts are English-only.
- **No RAG / vector store / embeddings / knowledge graph / agents** — analysis is a single-shot
  structured LLM call over role-scoped context; there is no retrieval pipeline.
- **No autonomous learning** — the system does not learn from user data; improvement comes from
  prompt versioning and provider/model updates.
- **No metrics/alerting stack** — monitoring is `/health`, `/health/db`, and structured JSON logs;
  no Sentry/Prometheus/metrics/tracing.
- **No load testing** — the design targets scale (indexes, pagination, stateless backend, dedup)
  but has not been load-tested (e.g., at 100k records); analysis runs synchronously per request.
- **Free-tier cold starts** — the Render free instance may take time to spin up after idle, so the
  first request after inactivity can be slow.

## Code quality rules

- TypeScript strict mode; Python type hints throughout
- No database queries inside route handlers; no duplicated business logic
- No secrets in source; no hard-coded AI responses or business intelligence
- No unnecessary dependencies, abstractions, or infrastructure (no Kubernetes, Kafka, Redis, etc.)
