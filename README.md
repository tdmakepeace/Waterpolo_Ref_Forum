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

On first start the app creates the bootstrap Admin (`role=admin`, `status=approved`) and, if the resources table is empty, imports the bundled referee catalog from [`data/resource_links.json`](data/resource_links.json).

If you forget that Admin password, set `reset_first_admin_password: true` in `config.yml`, restart the `web` service, log in, then set the flag back to `false`.

## Existing deployments

Pulling a newer image or git update does **not** change resource links that are already in the database. After you rebuild, import the catalog:

```bash
docker compose up -d --build
docker compose exec web python scripts/import_resource_links.py --dry-run
docker compose exec web python scripts/import_resource_links.py
```

The Flask equivalent is:

```bash
docker compose exec web flask import-resource-links --dry-run
docker compose exec web flask import-resource-links
```

Default behaviour inserts catalog URLs that are not already stored. Custom links with other URLs are left alone.

| Flag | Effect |
|------|--------|
| *(none)* | Insert missing catalog URLs only |
| `--update` | Also refresh title, description, and sort order for matching URLs. Does not change `is_active` |
| `--file path.json` | Import a custom JSON file instead of `data/resource_links.json` |
| `--dry-run` | Print added / updated / skipped counts without writing |

Without Docker:

```bash
python scripts/import_resource_links.py --file data/resource_links.json
```

Optional bootstrap helper (same first-admin and empty-table seed as app startup):

```bash
docker compose exec web python scripts/bootstrap_admin.py
```

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

## Resources

Active links appear in the sidebar and on `/resources`. Admins manage them at **Staff → Resource links**.

The bundled catalog in [`data/resource_links.json`](data/resource_links.json) is grouped for LWPL referees:

| Group | Examples |
|-------|----------|
| LWPL | League rules, sanctions form, referee allocations, match sheets |
| World Aquatics | Rules hub, current competition regulations PDF, water polo extract |
| Updates | June 2025 summary, tracked-changes PDF, Swim England briefings |
| Officials | Swim England hub, gradings, table-officials course |
| Videos | LEN/European Aquatics clinic playlist, Swim Ireland signals, CWPA library |
| BWPL | League rules and officials’ charter (if you also referee British League) |

JSON shape for a custom import file:

```json
{
  "links": [
    {
      "title": "LWPL — League Rules",
      "url": "https://lwpl.leaguerepublic.com/page/london_water_polo_league_rules.html",
      "description": "Optional notes for referees",
      "sort_order": 10,
      "is_active": true
    }
  ]
}
```

Match key is `url`. `--update` overwrites title, description, and sort order for that URL, but will not un-hide a link an Admin has deactivated.

LWPL rule 4.33 says matches follow FINA / Swim England rules where practical. Rule 4.34 still writes 7-minute quarters and a 30/20 shot clock; Swim England applied the World Aquatics June 2025 rules (including 28/18 possession) to English clubs from 1 July 2025. Confirm clock and period length for the fixture before play.

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

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests/test_app.py
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

On an empty SQLite database, startup still seeds the resource catalog. To add or refresh links later:

```bash
python scripts/import_resource_links.py --file data/resource_links.json
```

Production-like deployment still uses Docker Compose and PostgreSQL as in the steps above.
