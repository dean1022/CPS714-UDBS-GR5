# UDBS, Group 5: Netlify + Render + Supabase

The website (`public`) runs on Netlify, the Python backend (`backend`) runs on Render and the data is stored in Supabase (PostgreSQL).

## Deployment order
1. Create a Supabase project and open **SQL Editor**. Run `supabase/schema.sql`, then `supabase/seed.sql`. (Run seed only once on a fresh database.) This seed adds the sample books and the demo accounts (password hashes only). Database rules are fixed at 15 concurrent slots, 30 active loans and 15 holds. Passwords were not re-created.
2. In Supabase Connection settings copy the **Postgres connection string**, preferably its transaction/session pooler URL if your Render instance is IPv4-only. URL encode special characters in the password. Set SSL mode as required by Supabase. NEVER put this connection string in Netlify/public files.
3. Deploy this repo to **Render** as a Blueprint (`render.yaml`) or Python web service. Configure `DATABASE_URL`, `FRONTEND_ORIGIN` (exact Netlify site URL, without trailing slash) and `CRON_SECRET` in Render environment variables. Health check: `/api/health`.
4. Make sure `API_URL` in `public/src/common.js` is the Render HTTPS URL. This is a public API URL, not a secret.
5. Deploy the repository root to **Netlify**. The included `netlify.toml` publishes `public` and does not deploy Netlify functions.
6. E-books are PDFs in `backend/ebooks`. `GET /api/read/{id}` checks the active loan and only opens files from that folder.

## Code layout
- `backend/auth.py` and `backend/library.py` hold the login and lending rules, written as PostgreSQL queries with `%s` placeholders. `backend/database.py` opens the Supabase connection for each request.
- `supabase/schema.sql` creates the PostgreSQL tables and `supabase/seed.sql` adds the sample data.
- The browser JavaScript only shows pages and calls the API. All lending and login rules are in the backend.
- `backend/test_udbs.py` tests the backend rules. See `TESTING_INSTRUCTIONS.md` for how to run it and for the demo settings.

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
- Authentication uses salted SHA-256 password hashes for **demo compatibility only**. Use Argon2/bcrypt before real users.
- Current API uses bearer tokens in `sessionStorage` to work across Netlify and Render origins. This is for the university prototype, not a production authentication design.
- Expired loans are processed whenever borrowing/catalogue/library operations occur. For unattended expiry, schedule `POST /api/jobs/expire` with a `Bearer CRON_SECRET` header using an external scheduler. Render web service alone does not schedule this endpoint.
- Source backend timestamps are **naive local strings**. Set `TZ=UTC` on Render and treat stored timestamps consistently. Frontend countdown display is approximate if browser timezone differs. Migrate timestamps to `TIMESTAMPTZ` for production.
- Concurrent requests within one Render process are serialized by a lock. Multiple Render instances require PostgreSQL transaction-level locking to avoid overborrowing.
