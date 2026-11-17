# ElectroStock Backend Unit Test Report

| Run detail | Value |
| --- | --- |
| Tested revision | `b37cbd9` plus the origin configuration fix and additional tests in this change |
| Run date | 17 November 2026 |
| Environment | Windows, Python 3.11.9, pytest 9.1.1, pytest-cov 7.1.0, and disposable PostgreSQL 17 with TLS |
| Test suites | `backend/tests/unit` and `backend/tests/unit` + `backend/tests/integration`, measured independently |
| Coverage scope | `backend/app` |

## Test results

| Suite | Collected | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| Backend unit | 99 | 99 | 0 | 0 | 0 |
| Backend unit and integration | 200 | 200 | 0 | 0 | 0 |

The added unit cases exercise expired sessions, account removal and role changes, rate-limit expiry, browser-origin configuration, duplicate transaction requests, missing products, and sales that use exactly the remaining stock. The combined run also passed migrations, concurrent signup, demo seeding, and certificate and hostname verification against disposable PostgreSQL. Each run emitted one TestClient deprecation warning.

All 16 frontend tests passed separately with `npm test` under Node.js 22.19.0 after installing the locked dependencies in a clean copy.

## Coverage

| Suite | Line coverage | Branch coverage |
| --- | ---: | ---: |
| Original backend unit baseline | 71.07% (823 of 1,158) | 50.37% (137 of 272) |
| Updated backend unit | 74.83% (865 of 1,156) | 59.93% (163 of 272) |
| Updated backend unit and integration | 89.88% (1,039 of 1,156) | 79.41% (216 of 272) |

The configuration fix also changed the count of measurable lines by two. The table uses separate line and branch rates from the XML. Coverage measures `backend/app`. Frontend and browser test activity is outside those percentages.

## Reproduction and evidence

Run from the `backend` directory with the project's Python environment active and `docs/testing/reports` already created.

```powershell
python -m pytest tests/unit -v `
  --junit-xml=../docs/testing/reports/backend-unit-results.xml `
  --cov=app --cov-branch `
  --cov-report=term-missing `
  --cov-report=xml:../docs/testing/reports/backend-unit-coverage.xml
```

For the combined run, set `ELECTROSTOCK_TEST_POSTGRES_URL` to a disposable loopback PostgreSQL database named `electrostock_test_*` with an explicit port. Enable TLS with a certificate valid for `localhost` and set `ELECTROSTOCK_TEST_CA` and `ELECTROSTOCK_TEST_WRONG_CA` to the trusted and unrelated CA files. Run the following in the same directory.

```powershell
python -m pytest tests/unit tests/integration -v `
  --junit-xml=../docs/testing/reports/backend-unit-integration-results.xml `
  --cov=app --cov-branch `
  --cov-report=xml:../docs/testing/reports/backend-unit-integration-coverage.xml
```

- [Unit test results](backend-unit-results.xml) and [unit coverage](backend-unit-coverage.xml)
- [Unit and integration test results](backend-unit-integration-results.xml) and [combined coverage](backend-unit-integration-coverage.xml)
