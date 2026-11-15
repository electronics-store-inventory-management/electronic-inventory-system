# ElectroStock production deployment guide

Use a static frontend host for the Vite output, a persistent FastAPI web service, and managed PostgreSQL. Keep the browser and API on HTTPS. Run Alembic as a separate release step so API startup can only connect to the database. The repository is prepared for deployment and a public URL still requires team approval and hosting setup.

## Hosting choices and costs

The estimates below were checked on 2026-11-15. Check provider pricing, region, tax, transfer, storage, backup retention, and team seats before approving a plan.

| Option | Current public limits and trade-offs |
| --- | --- |
| Render Static Site | Suitable for the frontend on the organization repository. Static hosting shares workspace bandwidth and build allowances. Set a SPA rewrite in the dashboard. [Render static sites](https://render.com/docs/static-sites), [Render pricing](https://render.com/pricing) |
| Vercel | The repository includes a Vercel SPA rewrite. Hobby is for personal, non-commercial projects and cannot connect organization-owned Git repositories. Pro lists US$20/month with usage-based extras and team-seat considerations. [Vercel Hobby](https://vercel.com/docs/plans/hobby), [Vercel limits](https://vercel.com/docs/limits), [Vercel pricing](https://vercel.com/pricing) |
| Render FastAPI + Render PostgreSQL | A free web service can sleep after 15 idle minutes, and a free PostgreSQL database expires after 30 days. Render estimates an always-on Starter web service plus Basic-256mb PostgreSQL at about US$13/month before additional usage. Confirm backup retention for the chosen database tier. [Render free-tier limits](https://render.com/docs/free), [Render cost example](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses) |
| Supabase PostgreSQL | Free includes 500 MB per project, can pause after a week of inactivity, and excludes automatic backups. Pro starts at US$25/month and lists seven days of daily backups. A separate web service is still needed for FastAPI. [Supabase pricing](https://supabase.com/pricing) |

For a semester-long demo that should stay available afterward, start with a Render Static Site and budget for an always-on FastAPI service and paid persistent PostgreSQL. Fund the services only after the team approves the cost and assigns an owner. Budget alerts are preferable to assuming low traffic will stay free.

## PostgreSQL and API setup

1. Provision a managed PostgreSQL database for production or the public demo, separate from developer installs and previews. Render Postgres requires the **external** hostname for `verify-full`. Its internal certificates are self-signed and do not support this mode. Obtain the provider CA bundle through an authenticated provider channel, mount it as a file on the API host, and restrict database network access to the API service's egress and approved migration operators. For Supabase, choose a direct or session-pooler endpoint supported by your network and use the matching provider hostname and CA. [Render PostgreSQL connections](https://render.com/docs/postgresql-creating-connecting), [Supabase database connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
2. Create a Render web service from the GitHub repository with root directory `backend` and Python 3.11. Set the build command to `pip install -r requirements.txt` and the start command to `uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --no-access-log --no-proxy-headers`. Configure `/health` as the health check. Set the branch to `main` and leave automatic deployments disabled until the first release passes review. [Render Python configuration](https://render.com/docs/python-version), [Render health checks](https://render.com/docs/health-checks)
3. Add the backend environment variables below using the host's secret settings. Use a newly generated random JWT key and give it a stable value across normal redeployments. Rotation invalidates existing sessions.
4. From a trusted shell with the same database configuration, confirm the target database name and host. Run `python -m alembic current`, then `python -m alembic upgrade head`, then `python -m alembic current` from `backend`. Use a paid pre-deploy command or a single release operator for migrations. Migrate once per release before serving traffic. For existing data, make a backup first and review the [migration notes](../../backend/migrations/README.md). The signup release includes a revision that creates the existing account schema if the target has no users table. It leaves existing user tables and rows in place.
5. Start the API and request `/health`. Expect HTTP 200 with `{"status":"ok"}`. A database connectivity problem returns HTTP 503. Validate the Alembic revision independently since the health check probes connectivity.

## Environment variables

| Variable | Where | Example or default |
| --- | --- | --- |
| `APP_ENV` | Backend | `production` for hosted releases; `development` locally |
| `DATABASE_URL` | Backend secret | Required in production. Use the provider's certificate hostname and a URL-encoded password, for example `postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=verify-full`. Replace a provider-supplied `sslmode=require`. The app sets `verify-full` when omitted and rejects other URL query options in production. |
| `DATABASE_SSL_ROOT_CERT` | Backend | Required in production. Absolute path to the trusted PEM CA bundle, for example `/etc/secrets/postgres-ca.pem` if uploaded as a Render Secret File with that name. The API, Alembic, and CLI all need the file. |
| `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME` | Backend local alternative | Used when `DATABASE_URL` is empty; copy the backend example and set the local values. |
| `JWT_SECRET_KEY` | Backend secret | Random value of at least 32 characters in production. Generate it in your password manager or locally using a cryptographic generator. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | `30`; range 1–60 |
| `FRONTEND_ORIGIN` | Backend | Exact browser origin, for example `https://inventory.example.com`. Use no trailing slash. Development defaults to `http://localhost:5173`. |
| `REGISTRATION_ENABLED` | Backend | Defaults to `false` in production and `true` in development. Set `true` explicitly only on the isolated public demo with synthetic data. |
| `AUTH_TRUSTED_PROXY_NETWORKS` | Backend | Empty by default. Comma-separated ingress socket IPs or CIDRs confirmed by your provider and deployment checks. Wildcards and default routes are rejected. |
| `LOGIN_REQUESTS_PER_MINUTE` | Backend | `12` per client |
| `REGISTRATION_REQUESTS_PER_MINUTE` | Backend | `5` per client |
| `PORT` | Render runtime | Injected by the host into the start command |
| `VITE_API_BASE_URL` | Frontend, public build variable | `https://api.inventory.example.com`; use `http://localhost:8000` for a local build. Rebuild after changing it. |

The JWT algorithm is fixed at HS256. The backend uses one exact origin for CORS and accepts the authorization, content type, and transaction idempotency headers. Keep preview deployments pointed at a staging API with its own exact frontend origin and secrets. A Vite variable is public by design.

## Authentication ingress

Keep `--no-proxy-headers` in the start command so the app can inspect the original socket peer. Render documents forwarding client addresses via `X-Forwarded-For` through its edge and load balancers. Before enabling proxy trust on this service, obtain the actual trusted ingress socket IP ranges and confirm that the chain is overwritten or correctly appended by those proxies. Do not use Render's outbound IP list as a substitute. Set `AUTH_TRUSTED_PROXY_NETWORKS` to the confirmed addresses for each trusted hop and block any route that lets a client connect from those addresses without traversing the trusted ingress. The limiter walks the forwarded chain from right to left and stops at the first untrusted address. Direct and untrusted peers cannot set their identity via headers. [Render edge and client IP guidance](https://render.com/articles/how-render-handles-ddos-attacks), [Render secret files](https://render.com/docs/configure-environment-variables)

Run one API worker initially. If the trusted peers and chain cannot be confirmed, leave `AUTH_TRUSTED_PROXY_NETWORKS` blank and arrange rate limiting at a verified gateway before public launch. Proxied clients can share the same quota in this mode. Use a shared gateway or store when running multiple API workers or replicas. The app rejects auth POST bodies over 4 KiB, including streamed bodies. Configure ingress request timeouts to handle slow clients. Employees retain stock deduction access, so enable signup only on the isolated synthetic demo.

## Frontend, domains, and HTTPS

For Vercel set the root directory to `frontend`, select Vite, use Node.js 22.12+ and `npm ci` followed by `npm run build`, and publish `dist`. The included `vercel.json` allows refreshing BrowserRouter URLs. On Render Static Sites use root `frontend`, build command `npm ci && npm run build`, publish directory `dist`, and a rewrite from `/*` to `/index.html`. Set `VITE_API_BASE_URL` before building.

Use the host's TLS-backed default URL for the first smoke test. For optional custom domains, add the frontend and API domains to their respective providers, configure DNS as instructed, and wait until TLS is active. Update `FRONTEND_ORIGIN` and rebuild with the final API URL. Check `/login`, `/signup`, and a protected route by entering each URL directly.

## Initial admin and demo data

From a trusted shell configured for the target database:

```text
python -m app.cli create-admin demo_admin
python -m app.cli seed-demo --admin demo_admin
```

Create the admin once through the password prompt and save the password in your team's approved password manager. The command refuses to overwrite an account. Use the seed command only for the isolated demo database. Products and transactions are clearly marked and existing matching product names are skipped. Seed runs are serialized and each run commits its products, stock transactions, and audit records together. Public signup always assigns the employee role.

## Release verification

- Sign up with a private test employee account, then sign in and refresh a protected route.
- Confirm an employee can browse Products and Inventory, sees no Reports link or catalogue writes, and receives HTTP 403 from an admin-only API.
- Sign in as the admin and open Reports, add then delete a disposable product, and verify dashboard totals and recent movement.
- Check `/health`, allowed-origin preflight, nested-route refresh, and HTTPS. From the API host, verify a connection with the deployed PostgreSQL hostname and CA, and confirm a mismatched hostname and an untrusted CA each fail in an isolated verification environment. Keep `verify-full` if troubleshooting.
- In a disposable preview, exhaust one client's login quota and confirm a forged `X-Forwarded-For` value does not bypass it. Verify a second external client retains its own quota and that an oversized auth POST returns HTTP 413.
- Inspect logs for startup or database timeouts. Keep access and application logs free of request bodies, authorization headers, connection strings, and token values. For a CORS error compare the exact frontend origin to the backend setting. For an API startup error check that the production environment variables exist and the migration succeeded.

There is no email collection, verification, or password-reset email flow. Keep a managed admin password and arrange an authorized operator recovery process before public use.

## Backup, recovery, and releases

Enable the provider's automated backups and document retention and restore ownership. Take a fresh backup before schema changes, and store exports outside Git in restricted storage. If using `pg_dump`, use a protected connection configuration and a custom-format export. Rehearse restoration into a new database first; validate schema, users, and counts there before changing a production connection. Never expose the development database to the internet.

Have one person review the exact commit, run CI and migration checks, and release the approved revision. Use feature branches and separate preview resources for team development. Keep preview builds away from production secrets and data. During rollback, redeploy the last known good application revision after confirming schema compatibility; restore a database only with a reviewed recovery plan. Record the deployed commit, URLs, owner, and cost review date in team notes.
