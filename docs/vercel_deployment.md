# Vercel deployment

## Live production

**https://sentinel-banking-fraud.vercel.app/**

Workspace: `resum-projects`. Project: `sentinel-banking-fraud` (`prj_UpYrW9l6DIaQ7iggSsiIyGxuTEo3`). Production deployment: `dpl_ApiAmHi6QmU6w8jduNDLjZZdq4HY`.

The user explicitly approved creating and connecting a free Neon database. Dedicated resource `sentinel-banking-fraud-db` (`store_4Ulkr9OyL90DVvvm`) was provisioned on `free_v3` in `iad1`, with Neon Auth disabled, and connected only to this project's production and preview environments. No paid plan was selected. The database schema, roles and hosted administrator are initialized. It contains 2,400 explicitly synthetic transactions; local user accounts were not migrated.

## Verified behavior

Actual production HTTP checks, recorded in `deployment_verification.json`:

- Frontend and `/api/health`: 200; trained models available.
- Existing hosted administrator sign-in: 200; Secure and HttpOnly session cookie.
- Authenticated session, dashboard, model catalog and metrics: 200.
- Persistent dashboard reads 2,400 transactions.
- Current deployed model version is registered in PostgreSQL.
- Logout: 200; subsequent identity request: 401.
- Sign-in again with surrounding spaces and uppercase username: 200.
- Authenticated dashboard after the second sign-in: 200.
- Browser verified the production sign-in page and opened it for the user.

No temporary production accounts, investigation cases or adverse decisions were created for verification. Registration has automated API/form tests locally; its live endpoint is deployed but was not exercised by creating a production test account. Full local backend suite: 29 passing tests. Frontend: 15 tests passing in the latest frontend run; remote production compilation also passed.

## Hosted credentials and accounts

The cloud administrator username is `admin`. Its generated password is stored privately in ignored `.vercel/cloud-admin.env` and as an encrypted Vercel environment variable. Do not commit or upload this local file, or paste its password into documentation. Database connection settings are stored in ignored `.vercel/cloud.env` and in this project's provider-managed Vercel environment variables.

Use the permanent production URL above. Older immutable preview URLs retain their older configuration and should not be used for sign-in. Accounts created only in the local SQLite application were not migrated; users may create an Analyst account on the hosted app, or use the private hosted administrator credentials.

## Architecture and configuration

`vercel.json` declares two services: Vite at `/` and FastAPI for `/api/*` under one deployment origin. Linux uses CPU-only XGBoost. Remote builds generate trusted synthetic model artifacts. Local databases, user accounts, credentials, model artifacts, deployment caches and generated data files are excluded from uploads.

`DATABASE_URL` points to persistent SSL PostgreSQL. `ADMIN_USERNAME` / `ADMIN_PASSWORD` initialize the administrator only when absent. `COOKIE_SECURE=true` enables HTTPS cookies. `SEED_SYNTHETIC_DATA=false` avoids re-seeding during cold starts; the initial synthetic dataset was bulk-inserted and verified separately. Standard PostgreSQL URLs normalize to the psycopg driver. Hosted startup rejects SQLite, serializes schema/setup with advisory locks, and registers the actual deployed model metadata. Models are read-only at runtime and are retrained during a deployment build. Origin checks permit only configured origins and the exact injected Vercel deployment/production hostnames.

Deployment protection settings were preserved. A prior diagnostic CLI curl automatically created a bypass; that bypass was revoked and is not used by the production checks. Health verification used ordinary HTTPS requests without bypass tokens.

## Deploy updates

```text
vercel deploy --prod --scope resum-projects
```

The project is not connected to Git; CLI deployments publish local source. The CLI link lives in ignored `.vercel/` files. Model files are rebuilt in Vercel, not copied from the local machine. Verify `/api/health`, sign-in, session persistence, logout and database-backed reads after deployment.

## Earlier build history

An initial build exceeded the function bundle limit. Excluding deployment-tool caches and Linux GPU dependencies corrected it. The first ready preview had no database and failed startup; the traceback explicitly rejected SQLite in Vercel. Database provisioning initially required explicit approval. The user's later approval authorized the dedicated free database, and the production deployment and live sign-in checks above supersede that incomplete preview.

References: [Vercel Services](https://vercel.com/docs/services), [FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi), [Marketplace integration commands](https://vercel.com/docs/cli/integration).

## Post-sign-in analytics fix

A subsequent report exposed PostgreSQL GroupingError failures in transaction-trends and fraud-trends. The date extraction expression is now shared between SELECT, GROUP BY and ORDER BY so PostgreSQL sees identical bind parameters. The dashboard independently applies successful initial responses and names any panel that needs retry instead of discarding every response after one failure.

Production deployment `dpl_ApiAmHi6QmU6w8jduNDLjZZdq4HY` is READY at the same permanent URL. Verified live after deployment: identity, dashboard totals, transaction trends, fraud alerts, model metrics, agent performance, investigations and fraud trends all return 200 after login. Transaction trends contain 34 chronological daily groups totaling 2,400 transactions. No new production test accounts or investigations were created. The browser refresh could not be visually confirmed because the browser-control session timed out; the user should refresh the open page to load the new frontend. Prior browser snapshots showing Request failed belong to the superseded build.
