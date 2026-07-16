# Gemini Meeting Prep — Executive Briefing Console

An AI-powered executive assistant that automatically prepares briefing notes for your day's meetings. It pulls your Google Calendar events, cross-references recent Gmail conversations with each attendee, and asks Gemini to generate a concise, professional briefing for every meeting — all surfaced in a clean React dashboard.

> ⚠️ **This is the `main` branch.** It's a simpler, single-user setup meant for **running the project locally** on your own machine. It does **not** match what's deployed live.
>
> The **live demo** (https://assistant-frontend-q5li.onrender.com) runs from the separate **[`Render` branch](https://github.com/Sam00-B/gemini-meeting-prep/tree/Render)**, which adds multi-user Google OAuth (login-in-browser, session cookies), a Postgres-backed cache, and the Docker/`render.yaml` config needed to deploy on Render. If you're looking for the code behind the hosted demo, or want to deploy your own copy, use that branch instead. This README only covers `main`.

---

## How it works

1. On first run, a local OAuth consent screen opens in your browser and you sign in with Google (Calendar + Gmail read-only access). Tokens are cached to disk so you don't need to re-authenticate every time.
2. The backend fetches every remaining meeting on your calendar for today.
3. For each meeting, it searches Gmail for the last two weeks of correspondence with the attendees.
4. That context is handed to Gemini, which returns a short briefing: what the meeting is likely about, and bullet-point talking points drawn from the emails.
5. Briefings are cached in a local SQLite database so repeat runs for the same meeting are instant.
6. Everything renders as briefing cards in the frontend, with light/dark mode.

There are two ways to run the pipeline in this branch: as a **web app** (FastAPI + React) or as a **one-shot CLI script** that just prints briefings to your terminal.

---

## Architecture

```
┌─────────────────┐        ┌──────────────────────┐        ┌───────────────┐
│  React Frontend │  HTTP  │   FastAPI Backend      │        │  Google APIs  │
│  (Vite + TS +   │──────▶│   (app.py)              │───────▶│  Calendar +   │
│  Tailwind)       │◀──────│                         │◀───────│  Gmail        │
└─────────────────┘        │  - OAuth (auth.py, in-  │        └───────────────┘
                            │    browser, local-only) │
                            │  - Calendar (calendar_  │        ┌───────────────┐
                            │    service.py)          │───────▶│  Gemini API   │
                            │  - Gmail (gmail_         │◀───────│ (google-genai)│
                            │    service.py)           │        └───────────────┘
                            │  - Cache (database.py)  │
                            └──────────┬──────────────┘
                                       │
                                ┌──────▼──────┐
                                │   SQLite    │
                                │(briefings.db)│
                                └─────────────┘
```

### Backend (`/backend`) — FastAPI + Python

| File | Responsibility |
|---|---|
| `app.py` | FastAPI application. Exposes `GET /api/briefings` and orchestrates the calendar → Gmail → Gemini pipeline, caching results in SQLite. No login endpoints or session cookies — a single set of Google credentials is used for whoever runs the server. |
| `auth.py` | `authenticate_google_workspace()` — runs Google's standard **installed-app OAuth flow**: it spins up a temporary local server, opens your browser for consent, and saves the resulting token to `secrets/token.json` (or `/app/secrets/token.json` in Docker) for reuse on subsequent runs. |
| `calendar_service.py` | Calls `authenticate_google_workspace()` internally, then uses the Google Calendar API to fetch the user's remaining events for today (skips declined events, extracts title/time/attendees). |
| `gmail_service.py` | Also authenticates internally, then uses the Gmail API (batched requests) to pull recent email metadata (subject, sender, date, snippet) with each meeting's attendees, over a configurable lookback window. |
| `database.py` | A single SQLAlchemy model, `BriefingCache`, keyed by meeting title/time — no user/tenant concept, since this branch assumes one local user. Always uses SQLite at `sqlite:////app/data/briefings.db`. |
| `main.py` | Standalone CLI entry point. Run it directly (`python main.py`) to authenticate, pull today's meetings, and print AI briefings straight to the console — no web server required. |
| `Dockerfile` | Single-stage build on `python:3.12-slim`; installs `requirements.txt`, copies the app, and runs `uvicorn app:app` on port 8000. |

**Key differences from a "production" setup:**
- **Single-user only.** There's no login/logout, no session cookies, and no per-user data isolation — whoever's Google account is authenticated on the machine is the account used.
- **No cache-refresh endpoint.** Unlike a multi-user deployment, there's no `refresh` query parameter — cached briefings are reused indefinitely until the SQLite file is cleared.
- **Token persistence.** Google credentials are cached to a `token.json` file on disk rather than issued as a session cookie, so re-running the app won't require re-consenting each time.

### Frontend (`/frontend`) — React 19 + TypeScript + Vite + Tailwind CSS v4

- Single-page app (`src/App.tsx`) — "Executive Briefing Console."
- Calls a hardcoded `http://127.0.0.1:8000/api/briefings` endpoint (no environment-variable override in this branch) and renders each meeting as a card: title, time, attendee chips, and the Gemini-generated briefing rendered from Markdown (`react-markdown`).
- No "Authenticate with Google" button — authentication happens on the backend/CLI side, in your browser, the first time the Python process runs.
- "Sync & Compile Schedule" button fetches/refreshes the briefings.
- Light/dark theme toggle persisted to `localStorage`.
- Skeleton loading states and distinct empty states (idle vs. "no meetings today").
- Tests via Vitest + Testing Library (`App.test.tsx`); the Docker build runs `npm run test -- --run` before building, so a failing test blocks the image build.

### Running everything together: `docker-compose.yml`

The repo root includes a `docker-compose.yml` that builds and runs both services locally:

- **`backend`** — builds `backend/Dockerfile`, exposes port `8000`, mounts `./backend_data` for a persistent SQLite file, mounts `./backend` for live code reload during development, and mounts `./backend/secrets` so the container can find your `credentials.json`.
- **`frontend`** — builds `frontend/Dockerfile`, exposes port `5173` (mapped to Nginx's port `80` inside the container), and depends on `backend`.

---

## Tech stack

**Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy, SQLite, `google-genai`, `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`.

**Frontend:** React 19, TypeScript, Vite 8, Tailwind CSS 4, `react-markdown`, Vitest + Testing Library.

**AI model:** Google Gemini (`gemini-2.5-flash` in `main.py`).

**Infra:** Docker (single-stage builds), Docker Compose for local orchestration.

---

## Getting started locally

### Prerequisites
- Python 3.11+ (3.12 recommended, matching the Dockerfile)
- Node.js 22+
- A Google Cloud project with the **Calendar API** and **Gmail API** enabled, and an OAuth 2.0 Client ID (**Desktop app** type, since this branch uses the installed-app flow)
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
```

Run as a web API:
```bash
uvicorn app:app --reload --port 8000
```
The first request to `/api/briefings` will open a browser window for you to sign in with Google. The resulting token is cached to `backend/secrets/token.json` for future runs.

**Or**, skip the web server entirely and run the CLI version:
```bash
python main.py
```
This authenticates (if needed), fetches today's meetings, and prints each briefing directly to your terminal.

### 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` and click **Sync & Compile Schedule**. The frontend expects the backend to be running at `http://127.0.0.1:8000`.

### 3. Run everything with Docker Compose

From the repo root:
```bash
docker compose up --build
```
This builds and starts both the backend (port `8000`) and frontend (port `5173`), with your `backend/secrets/credentials.json` mounted into the container. Set `GEMINI_API_KEY` and `FRONTEND_URL` in a `.env` file at the repo root (or export them) so Compose can pass them through.

---

## API reference

### `GET /api/briefings`
Returns AI-generated briefings for the (single, locally-authenticated) user's remaining meetings today.

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
- There is no `refresh` parameter and no auth/login endpoints in this branch — those were added in `Render`.

---

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `GEMINI_API_KEY` | backend | Google Gemini API key (required) |
| `FRONTEND_URL` | backend (via `docker-compose.yml`) | Used for CORS `allow_origins` |

The frontend has no configurable API URL in this branch — it always targets `http://127.0.0.1:8000`.

---

## Repository structure

```
gemini-meeting-prep/           (main branch)
├── backend/
│   ├── app.py                 # FastAPI app & briefing pipeline (web mode)
│   ├── auth.py                 # Local installed-app Google OAuth flow
│   ├── calendar_service.py     # Google Calendar integration
│   ├── gmail_service.py        # Gmail integration
│   ├── database.py             # SQLAlchemy model (BriefingCache only)
│   ├── main.py                  # Standalone CLI script (prints briefings to console)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main UI
│   │   ├── App.test.tsx
│   │   └── ...
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
└── docker-compose.yml           # Local multi-container orchestration
```

---

## Known limitations

- **Single local user.** There's no concept of multiple accounts — the OAuth token cached in `secrets/token.json` determines whose calendar/Gmail is used.
- **No deployment config.** This branch has no `render.yaml` or equivalent; it's designed to run on your machine or in a local Compose stack, not on a hosting platform. For that, see the `Render` branch.
- **Hardcoded backend URL in the frontend.** `App.tsx` points directly at `http://127.0.0.1:8000`, so serving the frontend from anywhere other than localhost will require a code change.
