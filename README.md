# Water Polo Referee Forum

Self-hosted Q&A forum for water polo referees. Source: [https://github.com/tdmakepeace/Waterpolo_Ref_Forum](https://github.com/tdmakepeace/Waterpolo_Ref_Forum).

The build specification is [`build/waterpolo-referee-forum-plan.md`](build/waterpolo-referee-forum-plan.md).

## Requirements

- Docker Desktop or Docker Engine with Compose v2
- Copy of this repository

## First-time setup

1. Copy `config.example.yml` to `config.yml`.
2. Set database username/password (must match the Postgres values below), the water polo backdrop image URL, and the first Admin email/password.
3. Copy `.env.example` to `.env`.
4. Set a long random `SECRET_KEY`.
5. Keep these in **sync**:
   - `.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
   - `config.yml`: `database.username`, `database.password`, `database.name`
6. Start:

```bash
docker compose up --build
```

7. Open http://localhost:10010 and log in as the first Admin from `config.yml`.

On first start the app creates the bootstrap Admin (`role=admin`, `status=approved`). If you forget that password, set `reset_first_admin_password: true` in `config.yml`, restart the `web` service, log in, then set the flag back to `false`.

## Roles

| Role | Can |
|------|-----|
| User | Post, reply, vote, close own threads, change nickname/password |
| Supervisor | Everything a User can, plus lock/unlock, hide/unhide, delete posts, add/modify users |
| Admin | Everything a Supervisor can, plus approve registrations, issue password-reset links, manage resource links |

New self-registrations stay `pending_approval` until an **Admin** approves them. Supervisors can still create approved users directly from **Staff → Users**.

## Nickname

Optional at registration and on `/profile`. If blank, an 8-character random alphanumeric nickname is assigned. Existing questions keep the nickname snapshot from when they were posted.

## Listing

Questions are on **Open** and **Closed** tabs, ordered by vote score (up +1, down −1) then newest first. Hidden threads are omitted from those tabs and are only visible to Supervisors, Admins, and the original author.

## Config keys (`config.yml`)

| Key | Purpose |
|-----|---------|
| `database.*` | PostgreSQL connection used by the Flask app |
| `site_title` | Site name shown in the navbar and browser tab |
| `backdrop_image_url` | HTTPS URL of a water polo image used as the site backdrop |
| `first_admin.email` / `password` / `nickname` | Bootstrap Admin |
| `reset_first_admin_password` | If `true`, reset that Admin password on every web start |

`.env` holds `SECRET_KEY` and the Compose Postgres variables. Do not commit `.env` or `config.yml`.

For HTTP access (typical laptop Docker on port 10010), keep `SESSION_COOKIE_SECURE=false`. Set it to `true` only when the site is served over HTTPS.

## Backup

```bash
docker compose exec db pg_dump -U forum waterpolo_forum > backup.sql
```

## Local run without Docker (development)

If Docker is not installed, SQLite can be used:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set FLASK_APP=app:create_app
set SECRET_KEY=dev-secret-key-change-in-production-please
set DATABASE_URL=sqlite:///dev.db
flask db upgrade
flask run --host=127.0.0.1 --port=10010
```

Then open http://127.0.0.1:10010 and log in as the first Admin from `config.yml` (`admin@example.com` / `change-me-admin` in the example file).

Production-like deployment still uses Docker Compose and PostgreSQL as in the steps above.
