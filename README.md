# XConnect Backend (no UI)

A backend-only integration platform:
- User registration + login (JWT)
- SQLite (default) with SQLAlchemy, but supports any SQL via `DATABASE_URL`
- Credentials stored via a pluggable Secret Store:
  - `sqlite` (encrypted in DB with Fernet)
  - `aws` (AWS Secrets Manager)

Integrations included:
- GitHub (PAT token) -> list user repos
- ServiceNow (instance + username/password) -> validate auth, list tables
- Mapping storage: user selects GitHub repo + ServiceNow table

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# set ENCRYPTION_KEY if SECRET_STORE=sqlite
# set AWS creds if SECRET_STORE=aws
uvicorn api:app --reload
```

Open API docs:
- http://127.0.0.1:8000/docs

## Core endpoints
- POST `/api/auth/register`
- POST `/api/auth/login`
- GET  `/api/auth/me`

- PUT  `/api/integrations/github` (save token + validate)
- GET  `/api/github/repos`

- PUT  `/api/integrations/servicenow` (save creds + validate)
- GET  `/api/servicenow/tables`

- POST `/api/mappings` (repo -> table)
- GET  `/api/mappings`

## Notes
- `SECRET_STORE=sqlite` requires `ENCRYPTION_KEY` (Fernet key).
- Passwords are hashed with bcrypt.
- Secrets are never returned by the API.
