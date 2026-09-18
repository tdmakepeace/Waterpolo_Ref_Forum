# Water Polo Referee Rules Forum — Project Plan

**Document version:** 1.1  
**Date:** 18 September 2026  
**Purpose:** Implementation plan for a Flask-based forum where water polo referees can ask and discuss rules questions. Intended for submission and use as the build specification on a local development machine.  
**Git repository:** https://github.com/tdmakepeace/Waterpolo_Ref_Forum  
**Canonical path:** `build/waterpolo-referee-forum-plan.md`

**v1.1 changes:** three roles (User / Supervisor / Admin); optional and editable nicknames with random fallback; self-service password change; question voting with Open/Closed tabs; hidden threads; config-driven backdrop image, database credentials, and first-admin bootstrap/reset.

---

## 1. Executive Summary

Build a self-hosted web forum for water polo referees to post rules questions, receive threaded replies, vote on threads, and reference official resources. Users authenticate with email and password. New accounts require **Admin** approval. Questions are displayed under a public **nickname** (not the user’s real name). Each approved account has one role: **User**, **Supervisor**, or **Admin**. Supervisor matches Admin except for registration approval, manual password-reset issuance, and resource-link management.

Question owners can close their threads. Supervisors and Admins can lock, unlock, hide, or delete posts, and can add or modify users. Listings are split into **Open** and **Closed** tabs, ordered by vote score then newest first.

Source code lives at [https://github.com/tdmakepeace/Waterpolo_Ref_Forum](https://github.com/tdmakepeace/Waterpolo_Ref_Forum). The application and PostgreSQL database run as Docker containers orchestrated by Docker Compose. A gitignored `config.yml` holds the water polo backdrop image URL, database username and password, first Admin credentials, and a flag to reset that Admin password on service restart.

Password reset remains **manual** in v1 (Admin issues a reset link); logged-in users can also change their own password. The design leaves a clear hook for automated email later.

---

## 2. Goals and Non-Goals

### Goals (v1.1)

| Area | Requirement |
|------|-------------|
| Auth | Email + password login; secure session handling |
| Registration | Sign-up flow; account inactive until Admin approves |
| Nickname | User-defined, unique, public; optional; random alphanumeric if unset; editable on profile |
| Password | Logged-in user can change own password; Admin-initiated reset (manual) via one-time link |
| Roles | `user`, `supervisor`, `admin`; Supervisor = Admin except approval, manual reset, resource links |
| Forum | One question = one subject/thread; replies stay in that thread |
| Voting | Up (+1) / down (−1) on each question; listing ordered by score then newest |
| Listing | Separate **Open** and **Closed** tabs |
| Question lifecycle | Owner closes → no new replies; thread remains readable |
| Moderation | Supervisor and Admin: lock/unlock, hide/unhide, delete posts, add/modify users |
| Hidden | Hidden threads visible only to Supervisors, Admins, and the original author |
| Privacy | Questions show asker **nickname** only, never real name |
| Resources | Admin-managed links (e.g. FINA water polo rules) |
| Appearance | Site backdrop is an internet-sourced water polo image; URL in `config.yml` |
| Bootstrap | First Admin details in `config.yml`; optional password reset on service restart |
| Deployment | Flask app + SQL DB as containers; single `docker compose up` |

### Non-Goals (v1)

- Automatic password-reset emails (designed for, not implemented)
- Real-time chat / WebSockets
- Mobile native apps
- Full-text search (optional stretch)
- Multi-language UI
- Voting on individual replies (questions/threads only)

---

## 3. User Roles and Permissions

Every **approved** account has exactly one role: `user`, `supervisor`, or `admin`. Guest and pending/rejected are account **statuses**, not roles.

**Supervisor has the same capabilities as Admin, except** the three Admin-only actions: approve/reject registrations, issue manual password-reset links, and manage resource links.

| Action | Guest | Pending user | User | Supervisor | Admin |
|--------|-------|--------------|------|------------|-------|
| View open threads (not hidden) | Yes | Yes | Yes | Yes | Yes |
| View closed/locked threads (not hidden) | Yes | Yes | Yes | Yes | Yes |
| View hidden threads | No | No | Author only | Yes | Yes |
| Register | Yes | — | — | — | — |
| Login (when approved) | — | No | Yes | Yes | Yes |
| Post question / reply to open unlocked thread | — | No | Yes | Yes | Yes |
| Vote up/down on a question | — | No | Yes | Yes | Yes |
| Set / change own nickname | — | No | Yes | Yes | Yes |
| Change own password | — | No | Yes | Yes | Yes |
| Close own question | — | No | Yes (owner) | Yes (owner) | Yes |
| Reopen own closed question | — | No | Optional¹ | Optional¹ | Yes |
| Lock / unlock any question | — | No | No | Yes | Yes |
| Hide / unhide any question | — | No | No | Yes | Yes |
| Delete a question or reply | — | No | No | Yes | Yes |
| Add / modify users (role, details, deactivate) | — | No | No | Yes | Yes |
| View user real names (staff panel) | — | No | No | Yes | Yes |
| Approve / reject registrations | — | No | No | **No** | **Yes** |
| Issue manual password-reset link | — | No | No | **No** | **Yes** |
| Manage resource links | — | No | No | **No** | **Yes** |

¹ *Recommendation:* Allow owner to reopen only if staff have not locked the thread.

Supervisors receive **403** on Admin-only routes (`/admin/users/pending`, `/admin/reset-requests`, `/admin/links` and their POST endpoints).

---

## 4. Functional Requirements (Detailed)

### 4.1 Authentication and Accounts

**Registration**

1. User submits: email, password (with confirmation), optional display nickname (unique, public), optional real name (stored but never shown on the public forum).
2. If nickname is omitted or blank, assign a unique random nickname of 8 alphanumeric characters (retry on collision).
3. Password strength rules: minimum 8 characters; enforce via server-side validation.
4. Account created with status `pending_approval` and role `user`.
5. User sees: “Your account is awaiting admin approval.”
6. **Admin only** sees the pending list; can **Approve** or **Reject** (with optional reason). Supervisors cannot approve or reject.

**Login**

- Only users with status `approved` and `is_active=True` can log in.
- Failed login: generic message (“Invalid email or password”) to avoid email enumeration.
- Sessions: Flask-Login or signed cookies; configurable session lifetime (e.g. 7 days with “remember me”).

**Profile (logged-in user)**

- Edit nickname. If the field is cleared on save, assign a new random unique nickname.
- Change password: current password + new password + confirmation. On success, invalidate other sessions if practical; keep the current session.
- Nickname uniqueness is enforced on every change.

**Password reset (manual, v1) — Admin only**

1. User contacts Admin (out of band) or clicks “Request password reset” (creates a **reset request** record).
2. Admin dashboard: list of open reset requests. Supervisors cannot issue links.
3. Admin clicks “Issue reset link” → system generates single-use token (expires in 24h), displays link for Admin to send manually (email/Slack/etc.).
4. User opens link → set new password → token invalidated.
5. **Future:** Replace step 3 with SMTP/SendGrid; same token table and endpoint.

### 4.2 Forum — Questions and Replies

**Question (thread)**

- Fields: title, body (markdown or plain text), author (FK user), nickname snapshot at post time, created/updated timestamps, denormalized `score`, `is_hidden`.
- Status enum:
  - `open` — replies allowed (if not staff-locked)
  - `closed_by_owner` — owner satisfied; read-only for replies
  - `locked_by_admin` — Supervisor or Admin locked; read-only for replies
- `is_hidden` is independent of status. Hidden threads are omitted from public listings.
- Hidden visibility: **Supervisors, Admins, and the original author** only. Guests and other Users never see the thread in lists or by direct URL (404).
- Display: nickname, title, body, status badge, hidden badge (staff/author), vote score, reply count, last activity.

**Listing: Open and Closed tabs**

- **Open tab:** `status = open` and `is_hidden = false`.
- **Closed tab:** `status` in (`closed_by_owner`, `locked_by_admin`) and `is_hidden = false`.
- Sort both tabs by **`score` descending, then `created_at` descending** (newest first among equal scores).
- Supervisors, Admins, and authors of hidden threads can use a staff/author filter or badge to find hidden posts; those posts are not on the public tabs.

**Voting**

- Logged-in approved users may vote **up (+1)** or **down (−1)** on a question (thread), not on individual replies in v1.
- One vote per user per question. Changing vote replaces the previous value. Clearing a vote (optional) sets score contribution to 0.
- `questions.score` is the sum of vote values and is updated when a vote is cast or changed.

**Reply**

- Belongs to one question; ordered chronologically (flat chronological for v1).
- Author shown by nickname only.
- Cannot reply if question status is `closed_by_owner` or `locked_by_admin`, or if the question is hidden from the viewer.

**Owner actions**

- “Close question” on own threads → `closed_by_owner`.
- Optional: “Reopen question” → `open` (blocked if staff-locked).

**Supervisor and Admin actions**

- Lock → `locked_by_admin` (stops all replies).
- Unlock → `open` (recommend unlock → `open`, even if previously owner-closed).
- Hide / unhide → toggle `is_hidden`.
- Delete a question (cascade replies and votes) or delete an individual reply.
- Add users (email, password, nickname, role, status) and modify existing users (role, nickname, real name, active flag). Cannot use this path as a substitute for the Admin-only pending-approval queue: setting a pending user to `approved` via “modify user” is allowed for Supervisor (product decision: **allowed**, so Supervisors can activate accounts they created; they still cannot use the pending-approvals screen). *Recommendation:* Supervisor “add user” creates `approved` accounts directly; the registration pending queue remains Admin-only.

### 4.3 Resource Links (Admin only)

- Admin CRUD for links: title, URL, description (optional), sort order, `is_active`.
- Shown in sidebar or dedicated “Resources” page (e.g. “FINA Water Polo Rules”, local federation docs).
- Validate URLs server-side.
- Supervisors cannot access these endpoints.

### 4.4 Nickname Privacy

- Every question/reply stores `author_nickname` at time of posting (denormalized) so later nickname changes do not rewrite history.
- Templates never render `user.real_name` on public pages.
- Supervisor and Admin user-detail views may show email and real name for moderation.

### 4.5 Appearance

- Application backdrop is a CSS `background-image` using the HTTPS URL in `config.yml` (`backdrop_image_url`).
- The image is an internet-sourced water polo photograph. Do not bundle the image in the repo; load it from the configured URL.
- If the URL is missing or the image fails to load, fall back to a solid aquatic colour so the UI remains usable.

---

## 5. Technical Architecture

### 5.1 Stack

| Layer | Choice | Rationale |
|------|--------|-----------|
| Web framework | **Flask 3.x** | Lightweight, well-suited for forum scope |
| ORM | **SQLAlchemy 2.x** + **Flask-SQLAlchemy** | Mature SQL abstraction |
| Migrations | **Flask-Migrate (Alembic)** | Versioned schema |
| Auth | **Flask-Login** + **Werkzeug** password hashing | Standard Flask pattern |
| Forms | **Flask-WTF** + **WTForms** | CSRF protection |
| Templates | **Jinja2** + minimal CSS (**Bootstrap 5** or **Pico CSS**) | Fast, accessible UI |
| Database | **PostgreSQL 16** | Robust SQL, good Docker support |
| WSGI (prod) | **Gunicorn** | Production server in container |
| Reverse proxy (optional) | **Nginx** in compose | Static files + TLS termination later |
| App config | **`config.yml`** | Backdrop URL, DB credentials, first Admin, reset flag |

### 5.2 High-Level Diagram

```
┌─────────────┐     HTTP      ┌──────────────────┐
│   Browser   │ ────────────► │  web (Flask)     │
└─────────────┘               │  Gunicorn :5000  │
                              │  config.yml      │
                              └────────┬─────────┘
                                       │ SQL
                              ┌────────▼─────────┐
                              │  db (PostgreSQL) │
                              │  :5432           │
                              └──────────────────┘
```

Question listing flow:

```
Open tab or Closed tab
        │
        ▼
   is_hidden?
        │
        ├── yes, viewer is author / supervisor / admin → show with hidden badge
        ├── yes, viewer is guest or other user → omit (404 on direct URL)
        └── no → sort by score DESC, then created_at DESC
```

### 5.3 Application Structure

```
waterpolo-forum/                 # https://github.com/tdmakepeace/Waterpolo_Ref_Forum
├── build/
│   └── waterpolo-referee-forum-plan.md
├── docker-compose.yml
├── config.yml               # gitignored; local secrets and settings
├── config.example.yml       # committed template
├── .env.example             # SECRET_KEY (and compose helpers)
├── README.md
├── app/
│   ├── __init__.py          # App factory; load config; seed/reset first Admin
│   ├── config.py            # Merge YAML + env
│   ├── extensions.py        # db, login_manager, migrate
│   ├── models/
│   │   ├── user.py
│   │   ├── question.py
│   │   ├── reply.py
│   │   ├── vote.py
│   │   ├── password_reset.py
│   │   └── resource_link.py
│   ├── blueprints/
│   │   ├── auth.py          # login, register, reset, profile
│   │   ├── forum.py         # questions, replies, votes, tabs
│   │   ├── admin.py         # users, locks, hide, delete; Admin-only subroutes
│   │   └── main.py          # home, resources
│   ├── forms/
│   ├── templates/
│   └── static/
├── migrations/
├── Dockerfile
├── requirements.txt
└── scripts/
    └── bootstrap_admin.py   # Optional CLI; startup also runs the same logic
```

### 5.4 Data Model (SQL)

**users**

| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| email | VARCHAR UNIQUE | Login identifier |
| password_hash | VARCHAR | |
| nickname | VARCHAR UNIQUE | Public display name; auto-generated if unset |
| real_name | VARCHAR NULL | Staff only (Supervisor and Admin) |
| role | ENUM | `user`, `supervisor`, `admin` |
| status | ENUM | `pending_approval`, `approved`, `rejected` |
| is_active | BOOLEAN | Soft disable |
| is_bootstrap_admin | BOOLEAN | True for the config-defined first Admin |
| created_at | TIMESTAMPTZ | |

**questions**

| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| user_id | FK users | |
| author_nickname | VARCHAR | Snapshot |
| title | VARCHAR(200) | |
| body | TEXT | |
| status | ENUM | `open`, `closed_by_owner`, `locked_by_admin` |
| is_hidden | BOOLEAN | Default false |
| score | INT | Denormalized sum of votes; default 0 |
| created_at, updated_at | TIMESTAMPTZ | |

**replies**

| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| question_id | FK questions | ON DELETE CASCADE |
| user_id | FK users | |
| author_nickname | VARCHAR | Snapshot |
| body | TEXT | |
| created_at | TIMESTAMPTZ | |

**votes**

| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| user_id | FK users | |
| question_id | FK questions | ON DELETE CASCADE |
| value | SMALLINT | `+1` or `-1` only |
| created_at, updated_at | TIMESTAMPTZ | |
| UNIQUE | (user_id, question_id) | One vote per user per question |

**password_reset_tokens**

| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| user_id | FK users | |
| token_hash | VARCHAR | Store hash, not plain token |
| expires_at | TIMESTAMPTZ | |
| used_at | TIMESTAMPTZ NULL | |
| requested_at | TIMESTAMPTZ | User request timestamp |
| issued_by_admin_id | FK users NULL | Audit; Admin only |

**resource_links**

| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| title | VARCHAR | |
| url | VARCHAR | |
| description | TEXT NULL | |
| sort_order | INT | |
| is_active | BOOLEAN | |

**Indexes (recommended)**

- `questions(is_hidden, status, score DESC, created_at DESC)` — tab listings
- `replies(question_id, created_at)` — thread view
- `users(status)` — Admin pending queue
- `users(nickname)` — uniqueness / lookup
- `password_reset_tokens(token_hash)` — lookup on reset
- `votes(question_id)` — score recalculation if needed

---

## 6. Docker and Docker Compose

### 6.1 Services

**`db`**

- Image: `postgres:16-alpine`
- Volume: `postgres_data:/var/lib/postgresql/data`
- Environment: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` **must match** `config.yml` database settings
- Healthcheck: `pg_isready`

**`web`**

- Build: `Dockerfile` (Python 3.12-slim)
- Depends on: `db` (condition: service_healthy)
- Mount or copy `config.yml` into the container (read-only)
- Environment: `SECRET_KEY`, `FLASK_ENV` (from `.env`)
- Command: run migrations, then bootstrap/reset first Admin from config, then `gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"`
- Port: `10010:5000` (host 10010 → container 5000; or behind nginx `80:80`)

### 6.2 Example `docker-compose.yml` (outline)

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-waterpolo_forum}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    ports:
      - "10010:5000"
    environment:
      SECRET_KEY: ${SECRET_KEY}
      FLASK_ENV: ${FLASK_ENV:-production}
    volumes:
      - ./config.yml:/app/config.yml:ro
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

Compose Postgres variables must use the same username, password, and database name as `config.yml`. Document this in the README.

### 6.3 `config.example.yml`

```yaml
database:
  host: db
  port: 5432
  name: waterpolo_forum
  username: forum
  password: change-me

site_title: "LWPL - Referee Forum"
backdrop_image_url: "https://example.com/path/to/waterpolo-photo.jpg"

first_admin:
  email: admin@example.com
  password: change-me-admin
  nickname: HeadRef   # optional; random nickname if omitted

reset_first_admin_password: false
```

Copy to `config.yml` (gitignored) and set real values. `backdrop_image_url` must be a publicly reachable HTTPS image of water polo.

**Startup behaviour**

1. Load `config.yml`.
2. Ensure a user exists with `is_bootstrap_admin=True` (match on `first_admin.email`).
3. If missing: create that user as `role=admin`, `status=approved`, `is_active=True`, with the configured password (hashed) and nickname.
4. If `reset_first_admin_password` is `true`: set that user’s password hash to the configured password on **every** web process start. Operators should set the flag back to `false` after recovering access.

### 6.4 `.env.example`

```
SECRET_KEY=generate-a-long-random-string
FLASK_ENV=production
POSTGRES_USER=forum
POSTGRES_PASSWORD=change-me
POSTGRES_DB=waterpolo_forum
```

Do not commit `.env` or `config.yml`. Provide `.env.example` and `config.example.yml` only.

### 6.5 First-Time Setup (document in README)

1. Copy `config.example.yml` → `config.yml` and set database credentials, backdrop URL, and first Admin.
2. Copy `.env.example` → `.env`; set `SECRET_KEY`; keep Postgres vars in sync with `config.yml`.
3. `docker compose up --build -d`
4. Open `http://localhost:10010` and log in as the first Admin.

---

## 7. Security Considerations

| Topic | Approach |
|-------|----------|
| Passwords | Werkzeug `generate_password_hash` / `check_password_hash` |
| Sessions | HTTP-only, Secure cookies in production; strong `SECRET_KEY` |
| CSRF | Flask-WTF on all POST forms |
| SQL injection | SQLAlchemy parameterized queries only |
| XSS | Jinja2 auto-escaping; sanitize markdown if enabled |
| Reset tokens | Cryptographically random; store hash; single use; expiry |
| Rate limiting | Optional: Flask-Limiter on login/register (stretch) |
| Staff routes | `@supervisor_required` (supervisor or admin) for user management, delete, lock, hide |
| Admin-only routes | `@admin_required` for registration approval, manual password reset, resource links |
| Config secrets | `config.yml` and `.env` gitignored; never log passwords |
| Hidden threads | Enforce visibility in queries and on the detail view, not only in the template |

---

## 8. UI / Pages (Wireframe List)

| Route | Page |
|-------|------|
| `/` | Home — Open/Closed tabs, vote controls, water polo backdrop, resource links sidebar |
| `/register` | Registration form (nickname optional) |
| `/login` | Login |
| `/profile` | Change nickname and password |
| `/request-reset` | Submit password reset request |
| `/reset-password/<token>` | Set new password |
| `/questions` | Open tab (default) and Closed tab; score then date order |
| `/questions/new` | New question (auth) |
| `/questions/<id>` | Thread detail + replies + vote + close (owner) + staff actions |
| `/resources` | Public list of Admin-managed links |
| `/admin` | Staff dashboard (Supervisor and Admin) |
| `/admin/users` | Add/modify users (Supervisor and Admin) |
| `/admin/users/pending` | Approve/reject registrations (**Admin only**) |
| `/admin/reset-requests` | Issue reset links (**Admin only**) |
| `/admin/questions` | Lock/unlock, hide/unhide, delete |
| `/admin/links` | CRUD resource links (**Admin only**) |

Backdrop: apply `backdrop_image_url` as the page background on all public and authenticated layouts.

---

## 9. Implementation Phases

### Phase 1 — Foundation (≈ core scaffold)

- [ ] Repo layout, Flask app factory, load `config.yml` plus env
- [ ] Docker Compose + PostgreSQL + Dockerfile; DB credentials from config (compose env kept in sync)
- [ ] User model (`user` / `supervisor` / `admin`), migrations, password hashing
- [ ] Register / login / logout; optional nickname with random fallback
- [ ] On start: seed first Admin; honour `reset_first_admin_password`

**Deliverable:** Containers start; first Admin can log in from config.

### Phase 2 — Admin approval workflow

- [ ] `pending_approval` status on registration
- [ ] Admin pending users list + approve/reject (**Admin only**)
- [ ] Block login for non-approved users
- [ ] Supervisor receives 403 on pending-approval routes

**Deliverable:** Registration requires Admin approval.

### Phase 3 — Forum core

- [ ] Question and Reply models
- [ ] List/create question, view thread, post reply
- [ ] Open and Closed tabs; nickname-only display; nickname snapshot on post
- [ ] Votes (+1/−1), denormalized score, sort by score then newest
- [ ] Owner close question; enforce no replies when closed
- [ ] Profile: change nickname and password

**Deliverable:** Working Q&A forum with voting and profile self-service.

### Phase 4 — Staff moderation

- [ ] Supervisor and Admin: lock/unlock, hide/unhide, delete question or reply
- [ ] Hidden visibility (staff + author); 404 for everyone else
- [ ] Supervisor and Admin: add/modify users
- [ ] Permission matrix enforced in a services layer (`@supervisor_required` / `@admin_required`)

**Deliverable:** Full thread lifecycle and staff user management.

### Phase 5 — Password reset (manual, Admin only)

- [ ] Reset request from user
- [ ] Admin issues token + copyable link; Supervisor forbidden
- [ ] Reset password page
- [ ] Token expiry and one-time use

**Deliverable:** Manual reset flow end-to-end.

### Phase 6 — Resource links (Admin only)

- [ ] Admin CRUD for links; Supervisor forbidden
- [ ] Display on home / resources page
- [ ] Seed example: FINA water polo rules URL

**Deliverable:** Admin-managed links live.

### Phase 7 — Polish and handoff

- [ ] README with setup, `config.yml`, env vars, role guide
- [ ] Backdrop from `backdrop_image_url`; fallback colour
- [ ] Basic styling and responsive layout
- [ ] Error pages (404, 403)
- [ ] Logging (structured, no passwords in logs)

**Deliverable:** Production-ready v1 for laptop deployment.

### Phase 8 — Future (post-v1)

- [ ] SMTP config + automatic reset emails
- [ ] Email notification on reply (optional)
- [ ] Markdown editor for questions/replies
- [ ] Search
- [ ] Vote on replies
- [ ] TLS via nginx + Let’s Encrypt

---

## 10. Testing Strategy

| Type | Scope |
|------|-------|
| Unit | Model methods, permission helpers, nickname generator, token validation, score updates |
| Integration | Auth flows, approve user, close/lock/hide reply blocking, votes and sort, config Admin reset |
| Manual | Docker compose fresh install checklist; backdrop image loads |

Suggested tools: **pytest**, **pytest-flask**, in-memory SQLite or test PostgreSQL container for CI later.

**Critical test cases**

1. Pending user cannot log in.
2. Approved user can post a question; nickname shown, email/real name hidden.
3. Blank nickname at registration yields a unique random alphanumeric nickname.
4. User can change own nickname and password from `/profile`.
5. Closed question rejects new reply (403 or flash message).
6. Staff-locked question rejects reply even if owner tries.
7. Owner cannot close another user’s question.
8. Hidden question is visible to author, Supervisor, and Admin; 404 for guests and other Users.
9. Open/Closed tabs exclude hidden questions for the public; order is score DESC then created_at DESC.
10. Up vote then down vote by the same user results in score −1, not 0 from stacking.
11. Expired reset token rejected.
12. User cannot access `/admin/*`.
13. Supervisor can add/modify users, lock/hide, and delete posts.
14. Supervisor cannot approve registrations, issue reset links, or manage resource links (403).
15. Admin can perform all Supervisor actions plus the three Admin-only actions.
16. With `reset_first_admin_password: true`, restarting the web service resets the bootstrap Admin password to the config value.

---

## 11. Configuration and Secrets (Laptop Deployment)

| Source | Key | Purpose |
|--------|-----|---------|
| `config.yml` | `database.username` / `database.password` / `database.name` / `database.host` | PostgreSQL connection used by the app |
| `config.yml` | `site_title` | Site name in the navbar and page titles |
| `config.yml` | `backdrop_image_url` | Internet-sourced water polo backdrop |
| `config.yml` | `first_admin.email` / `password` / `nickname` | Bootstrap Admin |
| `config.yml` | `reset_first_admin_password` | If true, reset bootstrap Admin password on each web start |
| `.env` | `SECRET_KEY` | Flask session signing |
| `.env` | `FLASK_ENV` | `development` vs `production` |
| `.env` | `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose `db` service; must match `config.yml` |

Do not commit `.env` or `config.yml`. Provide `.env.example` and `config.example.yml` only.

---

## 12. Acceptance Criteria (v1.1 Complete)

1. `docker compose up --build` starts app and database without manual DB setup.
2. New user registers (optional nickname) → appears in Admin pending list → cannot log in until Admin approves. If no nickname is given, a random unique nickname is assigned.
3. Approved user can post a question; only nickname is visible on the question.
4. Logged-in user can change their nickname and password on `/profile`.
5. Other approved users can reply in the same thread and vote a question up or down.
6. Question lists appear on separate Open and Closed tabs, ordered by vote score then newest first.
7. Question owner can close the thread; no further replies; thread still readable by guests (unless hidden).
8. Supervisor and Admin can lock, unlock, hide, and unhide any thread; hidden threads are visible only to Supervisors, Admins, and the author.
9. Supervisor and Admin can add/modify users and delete questions or replies.
10. Supervisor cannot approve registrations, issue password-reset links, or manage resource links.
11. User can request password reset; Admin can generate a one-time link; user sets new password.
12. Admin can add/edit/delete resource links; links appear on the site.
13. Site backdrop uses the water polo image URL from `config.yml`.
14. First Admin is created from `config.yml` on first start; `reset_first_admin_password` resets that password on restart when true.
15. README documents full setup on a clean machine with Docker installed, including keeping compose env in sync with `config.yml`.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Nickname abuse | Unique nicknames; Supervisor/Admin can deactivate users |
| Spam registrations | Admin approval gate |
| Forgotten Admin password | `reset_first_admin_password` in `config.yml`; then set the flag back to false |
| Hotlinked backdrop fails | Fallback solid colour; document choosing a stable image URL |
| Vote brigading | One vote per user per question; auth required |
| Data loss | Named Docker volume for Postgres; document backup `pg_dump` |
| Config/compose credential drift | README: same username/password/db name in `.env` and `config.yml` |
| Scope creep | Strict v1 non-goals; email automation deferred |

---

## 14. Estimated Effort (for planning only)

| Phase | Relative size |
|-------|----------------|
| 1 Foundation | Medium |
| 2 Approval | Small |
| 3 Forum core | Large |
| 4 Moderation | Medium |
| 5 Password reset | Medium |
| 6 Resource links | Small |
| 7 Polish | Medium |

Single developer familiar with Flask: cohesive v1 in one focused build session across phases 1–7, with testing integrated per phase.

---

## 15. References

- GitHub repository: https://github.com/tdmakepeace/Waterpolo_Ref_Forum
- FINA / World Aquatics water polo rules (URL to be added by Admin at deploy time)
- Flask documentation: https://flask.palletsprojects.com/
- PostgreSQL Docker: https://hub.docker.com/_/postgres

---

## 16. Submission Checklist (Laptop)

When implementing on your laptop, use this plan with:

- [ ] This document (`build/waterpolo-referee-forum-plan.md`)
- [ ] Git repository: https://github.com/tdmakepeace/Waterpolo_Ref_Forum
- [ ] Docker Desktop or Docker Engine + Compose v2 installed
- [ ] `config.yml` copied from `config.example.yml` (backdrop URL, DB credentials, first Admin, reset flag)
- [ ] `.env` configured from `.env.example` (`SECRET_KEY`; Postgres vars matching `config.yml`)
- [ ] First Admin created automatically on first boot from `config.yml`

---

*End of plan.*
