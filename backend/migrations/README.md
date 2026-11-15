# Database migrations

Install the backend requirements, then run migrations from the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

For another virtual environment, use its Python executable in place of `.venv`.
Configure `DATABASE_URL` for hosted PostgreSQL, or use the existing
`DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, and
`DATABASE_NAME` environment variables for local PostgreSQL. Confirm the target
and back up existing data before applying migrations. The baseline revision creates
legacy tables only when absent; on a populated pre-Alembic database it leaves
existing tables and rows intact. The next revision adds stock checks, transaction
type and quantity checks, the product foreign key, and a nullable idempotency-key
column/index. The account revision creates the users schema on new databases and
validates existing account tables, including a generated integer primary key
and a non-partial unique constraint or index on username. If the revision reports
an incompatible table, back up the database and have an operator review and
repair the schema before retrying. The revision leaves existing user data in place.
Review existing data for negative stock, invalid transaction types,
and orphaned transaction product IDs before upgrading; those records will prevent
the constraints from being applied. New databases are initialized with
`alembic upgrade head`; the application no longer creates tables at startup.
