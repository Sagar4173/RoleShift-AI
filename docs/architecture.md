# RoleShift AI — Architecture

## System overview

```
┌─────────────────────┐
│   React Frontend    │  Vite + TypeScript (strict) + Tailwind CSS
│  (typed API client) │
└──────────┬──────────┘
           │ HTTP (JSON) — /api/v1, /health
           ▼
┌─────────────────────┐
│  FastAPI Backend    │  versioned API, Pydantic validation,
│   (application)     │  CORS via env, structured JSON logging,
│                     │  centralized error handling
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Service Layer     │  business logic; the only layer that
│                     │  combines repositories
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Repository Layer   │  all MongoDB access lives here;
│                     │  swap storage by replacing this layer
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│      MongoDB        │  Beanie ODM documents (typed, indexed)
│   (Atlas or local)  │
└─────────────────────┘
```

## Request flow

```
HTTP request
  → FastAPI route (app/api/routes/*)          — transport only, no logic
  → Pydantic schema validation (app/schemas)  — request/response contracts
  → Service (app/services/*)                  — business rules, error mapping
  → Repository (app/repositories/*)           — data access
  → Beanie document (app/models/*)            — MongoDB collection
```

Errors bubble back as consistent JSON: `{"detail": {"code", "message"}}`; internal details are
logged server-side and never exposed to clients.

## Data model (Phase 1)

| Collection        | Purpose                                              |
|-------------------|------------------------------------------------------|
| organizations     | Companies and their industry context                 |
| roles             | Roles within an organization                         |
| processes         | Business processes roles operate within              |
| activities        | Step-level activities per role and process           |
| skills            | Skills catalogue (current + future)                  |
| role_analyses     | Persisted, explainable AI analysis results (Phase 2 fills) |
| sources           | External references used during analysis             |
| analysis_runs     | Audit trail of analysis executions                   |

The `RoleAnalysis` document is fully structured and score-validated (scores in `[0, 1]`, nested
models reject unknown fields) so Phase 2's AI output can be persisted and re-read safely.

## Future: AI provider abstraction

```
                    ┌─────────────────────────────┐
                    │  AIProvider (Protocol)      │  app/services/ai/base.py
                    │  analyze_role(input)        │
                    │  health_check()             │
                    └──────────────┬──────────────┘
                                   │ Phase 2 implementations
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
         DeepSeekProvider   OpenAIProvider   GeminiProvider / OllamaProvider
```

Business logic depends only on the `AIProvider` protocol — providers are selected via configuration,
never hard-coded. No provider or fake implementation exists in Phase 1.

## Future: role analysis engine

```
POST /roles/{id}/analyze (Phase 2)
        │
        ▼
AnalysisService
        │ 1. gather structured context
        ▼
RoleAnalysisInput  (role, processes, activities, current skills)
        │
        ▼
AIProvider.analyze_role(input)          ← provider-agnostic
        │
        ▼
validate output against RoleAnalysis schema
        │
        ▼
persist RoleAnalysis + AnalysisRun      ← traceable, explainable
        │
        ▼
GET /roles/{id}/analysis returns the latest persisted analysis
```

Design rules that keep Phase 2 honest:

- **No static demo:** analysis must work for any new role, including surprise roles at demo time.
- **No hard-coded intelligence:** the engine operates on structured data from the database.
- **Persisted intelligence:** results are stored, not generated on the fly each view.
- **Explainable & traceable:** reasoning, model metadata, prompt version, and run records are stored.

## Backend layout

```
backend/app/
├── main.py            # app factory, CORS, exception handlers, lifespan
├── api/
│   ├── deps.py        # shared dependencies (settings)
│   ├── router.py      # aggregates /api/v1 routers
│   └── routes/        # health, organizations, roles, processes, activities, skills, analysis
├── core/              # config (env), logging (JSON), exceptions, database lifecycle
├── models/            # Beanie documents + enums + base document
├── schemas/           # Pydantic request/response models
├── repositories/      # data access layer (BaseRepository + per-entity)
└── services/
    ├── ai/base.py     # AIProvider protocol + input types (Phase 2 implementers)
    └── *_service.py   # organization, role, process, activity, skill, analysis
```

## Frontend layout

```
frontend/src/
├── components/ui/     # Card, Badge, PageHeader, EmptyState, StatCard
├── pages/             # Dashboard, Role Intelligence, Role Comparison, Settings, About
├── layouts/           # AppLayout (sidebar navigation + header)
├── services/api.ts    # centralized typed API client (no fetch in components)
├── hooks/useApi.ts    # loading/error/data hook
├── types/api.ts       # TypeScript mirrors of backend schemas
└── lib/utils.ts       # cn() helper
```

## Configuration & security

- Everything comes from environment variables or `.env` (`app/core/config.py`, Pydantic Settings).
- No database URLs, API keys, or credentials are hard-coded; `.env` is git-ignored.
- CORS origins are explicit and env-driven; no wildcard default in production.
- Logs are structured JSON and never include passwords, keys, or tokens.
- Clients receive clean JSON errors — never Python stack traces.