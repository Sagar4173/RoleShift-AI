# RoleShift AI

Role-level AI intelligence for the modern workforce — an enterprise application for the
**Modus Enterprise AI Build Challenge**.

**Selected assignment: Assignment 6 — Role-Level AI Intelligence**

The application analyzes the full role lifecycle:

```
Role → Processes → Activities → Current Skills
  → AI Exposure → Automated Activities → Augmented Activities
  → New Responsibilities → Future Skills → Future Role Profile
```

Everything is structured, persisted, explainable, and dynamically computable for **any** new role —
including surprise roles introduced live during the demo.

> **Current phase: Phase 1 — Production-quality foundation.**
> The AI engine, dashboards, and dynamic analysis arrive in Phase 2. No fake AI behavior exists anywhere in this codebase.

---

## Architecture overview

```
React frontend (Vite + TS + Tailwind)
        │  HTTP /api/v1
        ▼
FastAPI backend (versioned API)
        │
        ▼
Service layer (business logic)
        │
        ▼
Repository layer (MongoDB access)
        │
        ▼
MongoDB (Beanie ODM)
```

The AI provider is isolated behind a provider abstraction
(`backend/app/services/ai/base.py`) so DeepSeek, OpenAI, Gemini, Ollama, or any other provider can be
added in Phase 2 without touching business logic.

See [`docs/architecture.md`](docs/architecture.md) for the full design.

## Technology stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | React 18, TypeScript (strict), Vite 6, Tailwind CSS 4, React Router |
| Backend   | Python 3.13+, FastAPI, Pydantic v2, Pydantic Settings |
| Database  | MongoDB, Beanie ODM (Motor driver) |
| Dev       | Docker Compose (frontend, backend, MongoDB), pytest |

## Project structure

```
roleshift-ai/
├── frontend/                 # React + Vite + Tailwind
│   └── src/
│       ├── components/       # UI primitives
│       ├── pages/            # Dashboard, Role Intelligence, Comparison, Settings, About
│       ├── layouts/          # AppLayout (sidebar + header)
│       ├── services/         # Typed API client (no fetch scattered in components)
│       ├── hooks/            # useApi data-fetching hook
│       ├── types/            # TS types mirroring backend schemas
│       └── lib/
├── backend/                  # FastAPI + Beanie
│   ├── app/
│   │   ├── api/routes/       # /api/v1 endpoints
│   │   ├── core/             # config, logging, exceptions, database
│   │   ├── models/           # Beanie documents (incl. RoleAnalysis)
│   │   ├── schemas/          # Pydantic request/response validation
│   │   ├── repositories/     # data access layer
│   │   ├── services/ai/      # AI provider abstraction (interface only)
│   │   └── main.py           # application factory
│   └── tests/
├── docker-compose.yml        # mongo + backend + frontend
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

Tests run against an in-memory MongoDB (`mongomock-motor`) — no live database required.

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

| Variable          | Default                          | Description                                        |
|-------------------|----------------------------------|----------------------------------------------------|
| `APP_ENV`         | `development`                    | `development`, `staging`, `production`, `test`     |
| `LOG_LEVEL`       | `INFO`                           | Log verbosity (`DEBUG`…`CRITICAL`)                 |
| `APP_DEBUG`       | `false`                          | Debug mode flag                                    |
| `MONGODB_URL`     | `mongodb://localhost:27017`      | MongoDB connection string                          |
| `MONGODB_DATABASE`| `roleshift`                      | Database name                                      |
| `CORS_ORIGINS`    | `http://localhost:5173,…`        | Comma-separated allowed origins (no wildcard by default) |
| `API_V1_PREFIX`   | `/api/v1`                        | API version prefix                                 |

Frontend (optional): `VITE_API_BASE_URL` — backend base URL when not using the dev proxy.

## API documentation

- Live Swagger UI: <http://localhost:8000/docs>
- Live ReDoc: <http://localhost:8000/redoc>

### Phase 1 endpoints (`/api/v1`)

| Method | Path                              | Purpose                         |
|--------|-----------------------------------|---------------------------------|
| GET    | `/health`                         | Liveness probe                  |
| GET    | `/health/db`                      | MongoDB connectivity probe      |
| GET/POST | `/organizations`                | List / create organizations     |
| GET    | `/organizations/{id}`             | Fetch one organization          |
| GET/POST | `/roles`                        | List / create roles             |
| GET    | `/roles/{id}`                     | Fetch one role                  |
| DELETE | `/roles/{id}`                     | Delete a role                   |
| GET/POST | `/processes`                    | List / create processes         |
| GET/POST | `/activities`                  | List / create activities        |
| GET/POST | `/skills`                       | List / create skills            |
| GET    | `/roles/{id}/analysis`            | Latest persisted role analysis  |

> **Phase 2:** `POST /roles/{id}/analyze` will run the AI engine. It is deliberately absent in
> Phase 1 — no stubbed or fake behavior.

## Current phase (Phase 1) — what exists

- Typed, environment-based configuration (no hard-coded secrets or URLs)
- Beanie documents: Organization, Role, Process, Activity, Skill, **RoleAnalysis** (strongly typed,
  score-validated nested structures), Source, AnalysisRun — with sensible indexes
- Repository layer isolating all database access
- Service layer + AI provider abstraction (`services/ai/base.py`, interface only)
- Versioned REST API with Pydantic validation, consistent error responses, structured JSON logging
- Docker Compose for local development
- 24 passing backend tests; strict TypeScript frontend shell with typed API client

## Future phases

- **Phase 2:** AI provider implementation behind the abstraction, `POST /roles/{id}/analyze`
  dynamic role analysis, AnalysisRun execution tracking, persisted explainable intelligence,
  validation of provider output against the RoleAnalysis schema.
- **Phase 3+:** dashboards (role intelligence, comparison), AI assistant, source ingestion (RAG
  readiness), authentication, production hardening.

## Code quality rules

- TypeScript strict mode; Python type hints throughout
- No database queries inside route handlers; no duplicated business logic
- No secrets in source; no hard-coded AI responses or business intelligence
- No unnecessary dependencies, abstractions, or infrastructure (no Kubernetes, Kafka, Redis, etc.)