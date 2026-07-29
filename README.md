# StudyPilot AI

An AI-powered study planner for students on the UK education system — GCSE,
A Level and International A Level.

Upload your exam board's specification PDF and StudyPilot reads the units,
topics and content statements out of it, then builds a time-boxed timetable
around your exam dates, available hours, subject difficulty, weak areas and
remaining syllabus. Completing a topic books its spaced-repetition revisions
automatically; missing sessions feeds back into the plan.

| | |
|---|---|
| **Frontend** | React 18, Vite 6, Tailwind CSS, Radix UI, Framer Motion, Chart.js |
| **Backend** | FastAPI, SQLAlchemy 2, Alembic, PyJWT, bcrypt, pypdf |
| **Database** | SQLite in development, PostgreSQL in production |
| **Hosting** | Vercel (frontend) + Render (API and PostgreSQL) |

---

## What it does

- **Syllabus from a PDF.** Point it at an official AQA, Edexcel, OCR, CAIE or
  WJEC specification. The parser rebuilds the unit → topic hierarchy and keeps
  the board's own content statements as key points against each topic. It
  handles the awkward realities: running headers, dot-leader contents pages,
  headings that wrap mid-phrase, and the two different meanings of a bare `1.`
  depending on the board.
- **A planner that schedules by urgency.** Each subject gets a score from exam
  proximity, difficulty, priority, weak-subject status and coverage; days are
  filled block-by-block by largest deficit, so subjects interleave instead of
  batching.
- **Spaced repetition** at 2, 7 and 14 days plus a final pass three days before
  the exam.
- **Session reminders and a timer.** Two popups per session (five minutes
  before, and at the start), a pausable countdown, and an alarm when the
  session's scheduled slot ends.
- **Past papers by upload.** Drop the paper's PDF in and the cover page is read
  for subject, board, year, paper number, total marks and time allowed. Add
  your score inline afterwards; unscored papers stay out of the averages.
- **Analytics** — hours, coverage, streaks, exam readiness, improvement trend.

---

## Running locally

Requirements: Python 3.11+ and Node 18+.

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
cp .env.example .env            # defaults are fine for local work
python -m scripts.bootstrap     # runs migrations, verifies reference data
uvicorn app.main:app --reload --port 8000
```

API on http://127.0.0.1:8000 · interactive docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App on http://127.0.0.1:5173. The dev server proxies `/api` and `/uploads` to
port 8000, so everything is same-origin and no `VITE_API_URL` is needed.

### Checks

```bash
cd backend  && python -m scripts.bootstrap --check-only   # schema + data
cd backend  && python -m scripts.smoke_test               # 46 API checks
cd frontend && npm run lint
cd frontend && npm run build
```

`smoke_test` registers a throwaway account, walks the whole product path
(onboarding → syllabus upload → plan → sessions → revision → past paper upload
and scoring → analytics) and deletes the account afterwards. Point it at any
environment with `--base-url https://your-api.onrender.com`.

---

## Deployment

### Backend → Render

The repository contains a [Blueprint](render.yaml), so Render creates the
database and the API together:

1. Render dashboard → **New** → **Blueprint** → select this repository.
2. Apply. It provisions `studypilot-db` (PostgreSQL) and `studypilot-api`,
   generating `SECRET_KEY` itself and wiring `DATABASE_URL` between them.
3. After the frontend is live, set `FRONTEND_URL` on the service to its URL.
   Only needed for a custom domain — `*.vercel.app` is already allowed by a
   regex in `app/main.py`.

Migrations run in the start command (`alembic upgrade head && gunicorn …`), so
the schema is always current before the first request is served.

### Frontend → Vercel

1. Vercel → **Add New** → **Project** → import this repository.
2. Set **Root Directory** to `frontend`. Vite is detected automatically.
3. Add the environment variable `VITE_API_URL` = your Render URL, with no
   trailing slash and no `/api/v1` suffix.
4. Deploy.

`VITE_API_URL` is inlined at build time, so changing it needs a redeploy rather
than a restart.

`frontend/vercel.json` rewrites every unmatched path to `index.html`. Vercel
serves real files from `dist/` before applying rewrites, so hashed assets are
unaffected and the catch-all only picks up React Router paths — without it,
refreshing on `/planner` returns a 404.

---

## Environment variables

### Backend

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | production | `sqlite:///./studypilot.db` | Render's URL can be pasted as-is; the `postgres://` scheme is rewritten for SQLAlchemy 2 |
| `SECRET_KEY` | production | placeholder | JWT signing key. Startup **refuses** the placeholder when `ENVIRONMENT=production` |
| `ENVIRONMENT` | no | `development` | `production` enables the guards above and forces `DEBUG` off |
| `DEBUG` | no | `true` | Ignored in production |
| `FRONTEND_URL` | no | — | Added to CORS origins; needed for a custom domain |
| `BACKEND_CORS_ORIGINS` | no | localhost set | Comma separated |
| `UPLOAD_DIR` | no | `uploads` | Point at a mounted disk in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `1440` | |
| `REMEMBER_ME_EXPIRE_MINUTES` | no | `43200` | |

Generate a signing key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Frontend

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_URL` | production | API origin, e.g. `https://studypilot-ai-api.onrender.com`. Empty locally so the Vite proxy handles it |

---

## Known constraints on free hosting

- **Uploaded files do not survive a redeploy.** Render's free instances cannot
  mount a persistent disk, so the container filesystem is wiped on each deploy.
  Everything parsed *out* of an upload — units, topics, key points, paper
  metadata and scores — lives in PostgreSQL and is unaffected; only the
  original PDF download is lost. To keep the files, upgrade the service and
  uncomment the `disk:` block in `render.yaml` along with the `UPLOAD_DIR`
  override.
- **Cold starts.** Free services sleep after ~15 minutes idle; the next request
  waits roughly 50 seconds.
- **Free PostgreSQL expires.** Render deletes free databases after 30 days.
  Take a `pg_dump` or upgrade before then.

---

## Project layout

```
backend/
  app/
    api/v1/        route modules, one per feature area
    core/          config, security, dependencies, error handlers
    data/          subject catalogue, syllabus templates (ships with the code)
    db/            engine, session, schema bootstrap
    models/        SQLAlchemy models
    schemas/       Pydantic request and response models
    services/      planner, syllabus parser, past paper parser, analytics
  alembic/         migrations
  scripts/         bootstrap and smoke test
frontend/
  src/
    components/    UI primitives, layout, feature components
    context/       auth, theme, toasts, live study sessions
    hooks/         useFetch, usePending
    lib/           API client, helpers
    pages/         one per route, all lazily loaded
render.yaml        Render Blueprint (API + PostgreSQL)
```

## Database migrations

```bash
cd backend
alembic revision --autogenerate -m "what changed"
alembic upgrade head
alembic downgrade -1
```

Migrations render correctly for both SQLite and PostgreSQL — batch mode is
enabled automatically on SQLite, which cannot `ALTER` in place. Inspect the SQL
for a dialect without touching a database using
`alembic upgrade head --sql`.

## Licence

MIT
