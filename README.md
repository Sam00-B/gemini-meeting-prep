# Gemini Meeting Prep — Executive Briefing Console

An AI-powered executive assistant that automatically prepares briefing notes for your day's meetings. It pulls your Google Calendar events, cross-references recent Gmail conversations with each attendee, and asks Gemini to generate a concise, professional briefing for every meeting — all surfaced in a clean React dashboard.

> This document describes the **`Render`** branch, which adds full multi-user Google OAuth, a Postgres-backed cache, and Docker/Render deployment config on top of the original single-user prototype on `main`.

**Live demo:** https://assistant-frontend-q5li.onrender.com (deployed from this `Render` branch)
## 🧪 Live Demo & Authentication Note

You can interact with the live application using the **Demo Mode** button in the UI. This mode bypasses the OAuth flow and serves mocked data, allowing you to experience the frontend architecture and AI prompt formatting instantly.

**Why is live Google authentication restricted?**
Because this app requests restricted scopes (`gmail.readonly` and `calendar.readonly`), the Google Cloud project is intentionally kept in "Testing" mode. 
* Google caps refresh token lifetimes to 7 days for testing applications.
* Authentication is strictly limited to whitelisted developer emails to prevent unauthorized data access. 

*If you are reviewing my code and wish to run the full OAuth/Gemini pipeline locally, please see the Local Setup instructions below to configure your own GCP credentials.*

### Branches at a glance

| Branch | Purpose |
|---|---|
| `main` | Run the project **locally**. Simpler, single-user setup — no OAuth, no Docker, no Render-specific config. Good starting point for understanding the core Calendar → Gmail → Gemini pipeline. |
| `Render` | Run the project **on Render** (or any container host). Adds Google OAuth multi-user login, session cookies/JWT, a Postgres-backed cache, multi-stage Dockerfiles for both services, and `render.yaml` for one-shot Blueprint deployment. This is what powers the live demo above. |

---

## How it works

1. You sign in with Google (Calendar + Gmail read-only access).
2. The backend fetches every remaining meeting on your calendar for today.
3. For each meeting, it searches Gmail for the last two weeks of correspondence with the attendees.
4. That context is handed to Gemini, which returns a short briefing: what the meeting is likely about, and bullet-point talking points drawn from the emails.
5. Briefings are cached per-user in Postgres/SQLite so repeat visits are instant; a "force refresh" option lets you regenerate on demand.
6. Everything renders as briefing cards in the frontend, with light/dark mode.

---

## Architecture

```
┌─────────────────┐        ┌──────────────────────┐        ┌───────────────┐
│  React Frontend │  HTTP  │   FastAPI Backend      │        │  Google APIs  │
│  (Vite + TS +   │──────▶│   (app.py)              │───────▶│  Calendar +   │
│  Tailwind)       │◀──────│                         │◀───────│  Gmail        │
└─────────────────┘        │  - OAuth (auth.py)      │        └───────────────┘
                            │  - Calendar (calendar_  │
                            │    service.py)          │        ┌───────────────┐
                            │  - Gmail (gmail_         │───────▶│  Gemini API   │
                            │    service.py)           │◀───────│ (google-genai)│
                            │  - Cache (database.py)  │        └───────────────┘
                            └──────────┬──────────────┘
                                       │
                                ┌──────▼──────┐
                                │  PostgreSQL │
                                │  (or SQLite │
                                │  locally)   │
                                └─────────────┘
```

### Backend (`/backend`) — FastAPI + Python

| File | Responsibility |
|---|---|
| `app.py` | Main FastAPI application. Exposes `GET /api/briefings`, wires up CORS, session-cookie auth (`get_current_user`), and orchestrates the calendar → Gmail → Gemini pipeline with Postgres/SQLite caching. |
| `auth.py` | Google OAuth 2.0 (PKCE) login flow: `/auth/login` and `/auth/callback`. Issues a signed JWT stored in an `httpOnly` session cookie, and persists Google access/refresh tokens per user. |
| `calendar_service.py` | Uses the Google Calendar API to fetch the user's remaining events for the current day (skips declined events, extracts title/time/attendees). |
| `gmail_service.py` | Uses the Gmail API (batched requests) to pull recent email metadata (subject, sender, date, snippet) with each meeting's attendees, over a configurable lookback window. |
| `database.py` | SQLAlchemy models: `User` (OAuth identity + tokens) and `BriefingCache` (per-user cached AI briefings, keyed by meeting title/time). Auto-switches between SQLite (local) and Postgres (production) based on `DATABASE_URL`. |
| `main.py` | Legacy standalone CLI script from before multi-user auth was added. Prints briefings to the console for a single hardcoded user. Not used by the deployed app — superseded by `app.py`. |
| `Dockerfile` | Multi-stage build: installs dependencies into a venv, then copies into a slim runtime image running as a non-root user via `uvicorn`. |

**Key backend behaviors:**
- **Multi-tenant**: every user who logs in gets their own `User` row and isolated `BriefingCache` entries.
- **Caching**: briefings are cached by `(user_id, title, time)`. Calling `/api/briefings?refresh=true` purges and regenerates the cache for that day's meetings.
- **Auth**: OAuth uses PKCE with server-side state storage (in-memory dict keyed by OAuth `state`, expiring after 10 minutes) rather than relying on cookies during the handshake. On success, a 7-day JWT session cookie is set.
- **Credential storage**: expects a Google OAuth `credentials.json` file, located dynamically depending on environment — `/etc/secrets/credentials.json` (Render Secret Files), `/app/secrets/credentials.json` (Docker), or `backend/secrets/credentials.json` (local dev).

### Frontend (`/frontend`) — React 19 + TypeScript + Vite + Tailwind CSS v4

- Single-page app (`src/App.tsx`) — "Executive Briefing Console."
- Calls `GET /api/briefings` (with `credentials: 'include'` for the session cookie) and renders each meeting as a card: title, time, attendee chips, and the Gemini-generated briefing rendered from Markdown (`react-markdown`).
- "Authenticate Google Workspace" button redirects to the backend's `/auth/login` OAuth flow.
- "Sync & Compile Schedule" button triggers a force-refresh fetch.
- Light/dark theme toggle persisted to `localStorage`.
- Skeleton loading states and distinct empty states (idle vs. "no meetings today").
- Tests via Vitest + Testing Library (`App.test.tsx`); the Docker build runs `npm run test -- --run` before building, so a failing test blocks the image build.
- Production build is served via Nginx (`frontend/Dockerfile`) or Render's static site hosting.

### Deployment (`render.yaml`)

Defines three Render resources (Blueprint deploy):
1. **`assistant-backend`** — Docker web service built from `backend/Dockerfile`. Env vars: `PORT`, `DATABASE_URL` (auto-linked to the Postgres instance), `GEMINI_API_KEY` and `SESSION_SECRET_KEY` (set manually as secrets in the Render dashboard), `FRONTEND_URL`.
2. **`assistant-frontend`** — static site built with `npm install && npm run build`, published from `dist`. Env var `VITE_API_URL` points at the backend's public URL.
3. **`assistant-db`** — a free-tier managed PostgreSQL instance.

---

## Tech stack

**Backend:** Python 3.11, FastAPI, Uvicorn, SQLAlchemy 2.0, PostgreSQL (`psycopg2-binary`) / SQLite, PyJWT, `google-genai`, `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`.

**Frontend:** React 19, TypeScript, Vite 8, Tailwind CSS 4, `react-markdown`, Vitest + Testing Library.

**AI model:** Google Gemini (`gemini-3.1-flash-lite` in `app.py`; the older `main.py` script uses `gemini-2.5-flash`).

**Infra:** Docker (multi-stage builds for both services), Render Blueprints, managed Postgres.

---

## Getting started locally

### Prerequisites
- Python 3.11+
- Node.js 22+
- A Google Cloud project with the **Calendar API** and **Gmail API** enabled, and an OAuth 2.0 Client ID (Web application) with a redirect URI of `http://localhost:8000/auth/callback`
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/))

### 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Download your OAuth client credentials from Google Cloud Console and save them to:
```
backend/secrets/credentials.json
```

Create a `.env` file in `backend/`:
```env
GEMINI_API_KEY=your_gemini_api_key
SESSION_SECRET_KEY=some_long_random_string
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
# DATABASE_URL is optional locally — defaults to a local SQLite file
```

Run the API:
```bash
uvicorn app:app --reload --port 8000
```

### 2. Frontend setup

```bash
cd frontend
npm install
```

Create a `.env` file in `frontend/` (optional — defaults to `http://127.0.0.1:8000`):
```env
VITE_API_URL=http://localhost:8000
```

Run the dev server:
```bash
npm run dev
```

Visit `http://localhost:5173`, click **Authenticate Google Workspace**, and then **Sync & Compile Schedule**.

### 3. Run with Docker (both services)

Each service has its own multi-stage `Dockerfile` under `backend/` and `frontend/`. Build and run them individually, or adapt `render.yaml` for `docker-compose` if you prefer a one-command local stack.

---

## API reference

### `GET /api/briefings`
Returns AI-generated briefings for the authenticated user's remaining meetings today.

- **Auth:** requires a valid `session_token` cookie (set after OAuth login).
- **Query params:** `refresh` (bool, default `false`) — bypasses and clears the cache for today's meetings, regenerating fresh briefings.
- **Response:**
  ```json
  {
    "message": "Success",
    "briefings": [
      {
        "title": "Q3 Roadmap Sync",
        "time": "2026-07-15T15:00:00Z",
        "attendees": ["someone@example.com"],
        "ai_briefing": "**Context:** ...\n- Talking point one\n- Talking point two"
      }
    ]
  }
  ```

### `GET /auth/login`
Redirects to Google's OAuth consent screen (PKCE flow).

### `GET /auth/callback`
OAuth redirect target. Exchanges the auth code for tokens, upserts the `User` record, issues a session JWT as an `httpOnly` cookie, and redirects to `${FRONTEND_URL}/?login=success`.

### `GET /`
Health check — returns `{"status": "healthy", "service": "AI Executive Assistant API"}`.

---

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `GEMINI_API_KEY` | backend | Google Gemini API key (required) |
| `SESSION_SECRET_KEY` | backend | Secret used to sign session JWTs |
| `DATABASE_URL` | backend | Postgres connection string in production; falls back to local SQLite |
| `BACKEND_URL` | backend | Public URL of the backend, used to build the OAuth redirect URI |
| `FRONTEND_URL` | backend | Frontend origin, used for CORS and the post-login redirect |
| `VITE_API_URL` | frontend | Backend base URL the frontend calls |

---

## Known limitations / things to be aware of

- **`main.py` is legacy.** It predates the OAuth/multi-user rework and calls `get_today_meetings()` / `get_email_context()` without the `creds` argument they now require — it won't run as-is. The live app runs entirely through `app.py`.
- **In-memory OAuth state store.** `oauth_state_store` in `auth.py` lives in process memory, so it won't survive a restart or work correctly across multiple backend instances/replicas.
- **Read-only scopes.** The app only requests `calendar.readonly` and `gmail.readonly` — it never modifies calendar events or emails.
- **No test suite for the backend** — only the frontend has Vitest tests (run automatically during the Docker build).

---

## Repository structure

```
gemini-meeting-prep/
├── backend/
│   ├── app.py              # FastAPI app & briefing pipeline
│   ├── auth.py              # Google OAuth + JWT sessions
│   ├── calendar_service.py  # Google Calendar integration
│   ├── gmail_service.py     # Gmail integration
│   ├── database.py          # SQLAlchemy models (User, BriefingCache)
│   ├── main.py               # Legacy single-user CLI script
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main UI
│   │   ├── App.test.tsx
│   │   └── ...
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
└── render.yaml                # Render Blueprint (backend + frontend + Postgres)
```
