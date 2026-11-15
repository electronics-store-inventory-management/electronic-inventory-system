# Production readiness checklist

- [ ] Team approves host, database region, account owner, budget, and renewal reminder.
- [ ] Separate development, preview, and public-demo databases are provisioned.
- [ ] The managed database accepts its configured hostname and CA with `verify-full` and rejects a mismatch. A restricted backup exists before migrations and the restore policy is verified.
- [ ] Backend secrets are set in the host and excluded from Git and builds.
- [ ] One approved HTTPS frontend origin and the public HTTPS API URL are configured.
- [ ] Alembic is at head and `GET /health` returns 200.
- [ ] The SPA rewrite supports direct access to nested routes.
- [ ] A named admin signs in with credentials stored in the team's password manager.
- [ ] Public signup defaults to off and is enabled only on the isolated synthetic demo database.
- [ ] Employee signup, login, refresh, logout, and role restrictions pass.
- [ ] Product operations and admin Reports pass. Demo records contain no private data.
- [ ] Confirmed ingress peers or a verified gateway provide per-client quotas, forwarded-header spoofing fails, and oversized auth requests return HTTP 413.
- [ ] Sanitized logs and periodic uptime checks are verified.
- [ ] Production releases are restricted to reviewed revisions and the previous deployment can be restored.
