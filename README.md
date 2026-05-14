# SIAHL TTS Replacement

FastAPI app for SIAHL standings, schedules, and team rosters, backed by the public TimeToScore API described in [tts_api_notes.md](./tts_api_notes.md).

## What Exists Now

- FastAPI app with server-rendered pages
- Internal service layer for TimeToScore requests
- Request-signing helper
- Basic TTL caching
- Routes for standings, schedule, and team pages
- Mock-data fallback for development when live upstream credentials are not configured

## Local Run

1. Create a virtualenv and install dependencies.
   Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Export the live TimeToScore credentials:

```bash
export TTS_API_KEY="web"
export TTS_API_SECRET="..."
```

3. Run the app:

```bash
uvicorn app.main:app --reload
```

4. Open `http://127.0.0.1:8000`.

If `TTS_API_KEY` and `TTS_API_SECRET` are set, the app uses live TimeToScore data by default.
If they are missing, the app falls back to built-in mock data so the UI can still render.

## Environment

Required for live data:

```bash
export TTS_API_KEY="web"
export TTS_API_SECRET="..."
```

Everything else is optional. The app already defaults to:

```bash
APP_NAME="SIAHL"
LEAGUE_ID=1
CURRENT_SEASON_ID=74
CURRENT_STAT_CLASS_ID=1
TTS_API_BASE="https://api.sharksice.timetoscore.com"
TTS_SITE_BASE="https://stats.sharksice.timetoscore.com"
PREWARM_ON_STARTUP=true
REFRESH_META_INTERVAL_SECONDS=21600
REFRESH_STANDINGS_INTERVAL_SECONDS=600
REFRESH_SCHEDULE_INTERVAL_SECONDS=600
```

Only set overrides if you want behavior different from those defaults. Example:

```bash
export USE_MOCK_DATA=true
export REFRESH_STANDINGS_INTERVAL_SECONDS=600
```

## Cache And Refresh

The app uses an in-memory TTL cache and can also prewarm/refresh hot data in the background.

Current default behavior:

- prewarm metadata, all standings, and upcoming schedule on startup
- refresh metadata every 6 hours
- refresh standings every 10 minutes
- refresh upcoming schedule every 10 minutes

The cache is process-local, so each app worker maintains its own cache.

## EC2 Deployment Shape

Use a dedicated subdomain such as `siahl.fredhope.com`.

Recommended setup:

- Route 53 `A` or `CNAME` record for `siahl.fredhope.com`
- `nginx` vhost for that hostname
- app process bound on `127.0.0.1:8000`
- `systemd` service running `gunicorn` with uvicorn workers

Example `gunicorn` command:

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8000 app.main:app
```

Example `nginx` proxy target:

- `proxy_pass http://127.0.0.1:8000;`

## Current Limitations

- The upstream schedule endpoint can be slow with some filter combinations, so the app currently infers division for the global schedule from team metadata when needed.
- Current season is configured, not auto-discovered at runtime.
