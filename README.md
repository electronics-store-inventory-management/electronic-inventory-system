# ElectroStock

ElectroStock helps electronics-store teams manage a product catalogue, monitor stock, and review inventory activity. It is a university software engineering project with a React and Vite frontend, a FastAPI API, and PostgreSQL via SQLAlchemy and Alembic.

**Demo URL:** Pending hosting approval.

## Features

- Public username signup creates employee accounts. An administrator provisions admin accounts through a separate local command.
- Products supports search and details for employees, with catalogue creation, editing, and deletion for administrators.
- The dashboard reads actual stock value, low and out-of-stock items, and recent transactions from the API.
- Inventory and Reports use the same stock status rules. Reports and product writes are admin-only.
- The Suppliers page shows supplier records to signed-in users and gives administrators create and edit controls.
- The Transactions page shows stock history. Employees can record sales, and administrators can also receive stock or correct the balance.
- The API records product changes, supplier changes, and stock transactions in the audit log.

## Architecture

The browser uses a Vite-built React app and sends requests to FastAPI over HTTP locally and HTTPS in production. The API issues short-lived bearer tokens. The frontend uses the authenticated account endpoint for display and navigation, and the API checks the current database role on protected requests. PostgreSQL stores inventory, accounts, and audit records.

See the [Software Architecture and Design Specification](docs/architecture/Software_Architecture_and_Design.md) for component diagrams, sequence diagrams, and API contracts.

## Run locally

Use Python 3.11, Node.js 22.12 or newer, and a local PostgreSQL database you created for development. Run these commands from the repository root in PowerShell:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pytest httpx
Copy-Item .env.example .env
# Set your PostgreSQL connection and a random JWT_SECRET_KEY in .env.
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second terminal, from the repository root:

```powershell
Set-Location frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Create an employee account at **Create an account**. To test admin features, use an existing development admin or run `python -m app.cli create-admin demo_admin` from `backend` in the activated virtual environment. The CLI prompts for a password without echoing it. The deployment guide explains how to seed isolated demo data.

If you use a different frontend host or port, set `FRONTEND_ORIGIN` in `backend/.env` to the exact browser origin and restart the API.

## Checks

From `backend` in the activated virtual environment:

```powershell
python -m pytest
```

From `frontend`:

```powershell
npm test
npm run lint
npm run build
```

The build reads `VITE_API_BASE_URL` from `.env.local` or the build environment. Most backend tests use temporary SQLite databases. To run the PostgreSQL migration, concurrent signup, and demo seed tests locally, provision a disposable loopback PostgreSQL instance and set `ELECTROSTOCK_TEST_POSTGRES_URL` to an explicit port and a database named `electrostock_test_*`. CI runs these checks against its temporary database service. Never point the tests at a development or hosted database.

See the [software test plan](docs/testing/Software_Test_Plan.md), [backend test and coverage results](docs/testing/reports/Unit_Test_Report.md), and [system test results](docs/testing/reports/System_Test_Report.md).

The PostgreSQL TLS regression also requires `ELECTROSTOCK_TEST_CA` and `ELECTROSTOCK_TEST_WRONG_CA` pointing to separate local PEM CA files. Configure the disposable server with a certificate signed by the first CA and valid only for `localhost`. The test checks successful TLS and rejects both a hostname mismatch and the unrelated CA.

## Deployment

Use a static host, a FastAPI web service, and managed PostgreSQL. Keep production and preview databases separate. See the [production deployment guide](docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md) and [readiness checklist](docs/deployment/PRODUCTION_READINESS_CHECKLIST.md).

## Future work

Consider invitation-based signup for private inventory and a verified recovery workflow when the team has an email provider.
