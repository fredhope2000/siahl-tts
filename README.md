# SIAHL TTS Replacement

FastAPI app for SIAHL standings, schedules, and team rosters, backed by the public TimeToScore API described in [tts_api_notes.md](./tts_api_notes.md).

## What Exists Now

- FastAPI app with server-rendered pages
- Internal service layer for TimeToScore requests
- Request-signing helper
- Basic TTL caching
- Routes for standings, schedule, and team pages
- Mock-data fallback when live upstream credentials are not configured

## Local Run

1. Create a virtualenv and install dependencies.
   Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
uvicorn app.main:app --reload
```

3. Open `http://127.0.0.1:8000`.

If `TTS_API_KEY` and `TTS_API_SECRET` are not set, the app runs in mock-data mode.

## Environment

```bash
export APP_NAME="SIAHL"
export LEAGUE_ID=1
export CURRENT_SEASON_ID=74
export TTS_API_BASE="https://api.sharksice.timetoscore.com"
export TTS_SITE_BASE="https://stats.sharksice.timetoscore.com"
export TTS_API_KEY="web"
export TTS_API_SECRET="..."
export USE_MOCK_DATA=false
```

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

- Upstream response normalization is intentionally defensive because real payload samples are not yet checked into this repo.
- Team metadata discovery may need refinement once live responses are inspected.
- Current season is configured, not auto-discovered.
