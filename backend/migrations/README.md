# Database migrations

Install the backend requirements, then run migrations from the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

For another virtual environment, use its Python executable in place of `.venv`.
Configure the PostgreSQL connection with the existing `DATABASE_USER`,
`DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, and `DATABASE_NAME`
environment variables before applying migrations. The baseline revision creates
legacy tables only when absent; on a populated pre-Alembic database it leaves
existing tables and rows intact. The next revision adds stock checks, transaction
type and quantity checks, the product foreign key, and a nullable idempotency-key
column/index. Review existing data for negative stock, invalid transaction types,
and orphaned transaction product IDs before upgrading; those records will prevent
the constraints from being applied. New databases are initialized with
`alembic upgrade head`; the application no longer creates tables at startup.
