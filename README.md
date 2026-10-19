# UDBS, Group 5: Netlify + Render + Supabase

This version keeps the original Python logic from Kusal and Megan and the Sprint 1 HTML/CSS/DOM frontend. The JavaScript Netlify backend has been removed, not translated line-by-line: original `library.py` and `auth.py` run on Render through `api.py`.

## Deployment order
1. Create a Supabase project and open **SQL Editor**. Run `supabase/schema.sql`, then `supabase/seed.sql`. (Run seed only once on a fresh database.) This seed exports the merged SQLite data, including dummy account hashes. Database rules are fixed at 15 concurrent slots, 30 active loans and 15 holds. Passwords were not re-created.
2. In Supabase Connection settings copy the **Postgres connection string**, preferably its transaction/session pooler URL if your Render instance is IPv4-only. URL encode special characters in the password. Set SSL mode as required by Supabase. NEVER put this connection string in Netlify/public files.
3. Deploy this repo to **Render** as a Blueprint (`render.yaml`) or Python web service. Configure `DATABASE_URL`, `FRONTEND_ORIGIN` (exact Netlify site URL, without trailing slash) and `CRON_SECRET` in Render environment variables. Health check: `/api/health`.
4. In `public/src/common.js`, replace `__RENDER_API_URL__` with your Render HTTPS URL, for example `https://udbs-python-api.onrender.com`. This is a public API URL, not a secret.
5. Deploy the repository root to **Netlify**. The included `netlify.toml` publishes `public` and does not deploy Netlify functions.
6. Add dummy documents under `backend/ebooks` and update the relevant `literature.file_url` in Supabase to its **filename**. `GET /api/read/{id}` checks the active loan in Python and only opens files from the bundled ebooks directory.

## Original authors' source
- `original_python/` contains the original merged backend (including its SQLite database module), for reference and comparison. **Never deploy original_python as the application.**
- `backend/auth.py` and `backend/library.py` preserve login and lending rules. `backend/database.py` adapts their SQLite parameter syntax and result row operations to PostgreSQL.
- `supabase/schema.sql` converts the original SQLite schema to PostgreSQL; `supabase/seed.sql` exports rows from the original SQLite database.
- The browser JavaScript is DOM and HTTP code, not replicated lending/authentication business logic.

## Local API
```
cd backend
python -m venv .venv
# activate your virtualenv
pip install -r requirements.txt
# Set DATABASE_URL and FRONTEND_ORIGIN in your terminal environment
uvicorn api:app --reload
```

Netlify local preview needs the frontend configured to reach your Render URL or local Python URL and CORS set accordingly.

## Important constraints
- Authentication uses Megan's original salted SHA-256 password hashes for **demo compatibility only**. Use Argon2/bcrypt before real users.
- Current API uses bearer tokens in `sessionStorage` to work across Netlify and Render origins. This is for the university prototype, not a production authentication design.
- Expired loans are processed whenever borrowing/catalogue/library operations occur. For unattended expiry, schedule `POST /api/jobs/expire` with a `Bearer CRON_SECRET` header using an external scheduler. Render web service alone does not schedule this endpoint.
- Source backend timestamps are **naive local strings**. Set `TZ=UTC` on Render and treat stored timestamps consistently. Frontend countdown display is approximate if browser timezone differs. Migrate timestamps to `TIMESTAMPTZ` for production.
- Concurrent requests within one Render process are serialized by a lock. Multiple Render instances require PostgreSQL transaction-level locking to avoid overborrowing.
- Run real end-to-end tests against your own deployed Supabase/Render/Netlify project. Those services cannot be deployed using this ZIP alone.
