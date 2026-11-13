# COBI demo deployment

This repository deploys as one Vercel project from the repository root. Vercel builds the React/Vite interface and serves it with the FastAPI application. The API stores account-scoped demonstration cases in Neon Postgres; Neon Auth handles email/password sign-in.

## Demo boundary

This configuration is for a personal, synthetic-data demonstration on Vercel Hobby. Do not put real applicant, banking, identity or repayment data into it. The score is illustrative, not calibrated or validated for lending, and a human remains the decision maker. Vercel restricts Hobby to personal, non-commercial use; move to an eligible paid plan before using the platform for a commercial purpose.

## Deployment settings

- The current personal demo project is `cobi-demo` at `https://cobi-demo.vercel.app`, connected to `Tung-Quan/COBI` with `commercial-demo-setup` as its Production branch.
- Import `Tung-Quan/COBI` into the `tung-quan` Vercel account.
- Keep the Root Directory at `.` (the repository root).
- Keep the checked-in `vercel.json` build settings. The FastAPI app discovers the built interface under `frontend/dist` and serves it from the same origin as `/api`.
- The API function runs in Singapore (`sin1`) near the demo database.
- Leave Vercel's Node.js install behavior overridden only by the checked-in `npm ci --legacy-peer-deps --prefix frontend` command; `pyproject.toml` declares the Python entry point and runtime packages.

## Environment variables

Add these in the Vercel project settings for Preview and Production:

| Variable | Value | Visibility |
| --- | --- | --- |
| `DATABASE_URL` | Pooled connection URL for Neon project `cobi-demo`, database `cobi` | Secret, server only |
| `NEON_AUTH_BASE_URL` | Neon Managed Auth URL ending in `/cobi/auth` | Server setting |
| `NEON_AUTH_JWKS_URL` | Neon Auth JWKS endpoint ending in `/cobi/auth/.well-known/jwks.json` | Server setting |
| `VITE_NEON_AUTH_URL` | The same Neon Managed Auth URL | Public build variable |

Do not prefix database credentials or private keys with `VITE_`; Vite variables are included in browser code. The Auth URL and JWKS endpoint are public identifiers, while the Postgres connection URL is a privileged secret.

## Database setup

Before the first deployment, apply `backend/migrations/0001_demo_tenant_schema.sql` to the `cobi` database. The migration creates account-scoped application, audit and calculation tables. The app seeds the six synthetic example cases the first time each user opens the workspace.

## Neon Auth trusted domain

After Vercel creates the project URL, add that exact HTTPS origin (without a trailing slash) to Neon Auth's trusted domains. For example, add `https://<project>.vercel.app`. Localhost is already supported by the local development setup.

## Local development

Install the frontend and backend dependencies, then run FastAPI and Vite in separate terminals:

```powershell
python -m pip install -r requirements.txt
npm ci --legacy-peer-deps --prefix frontend
```

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

```powershell
npm --prefix frontend run dev
```

With no Neon variables, the local app uses the existing SQLite synthetic workspace. Set `VITE_API_BASE_URL` only if the frontend and API are intentionally hosted on separate origins; this deployment keeps them on the same origin.
