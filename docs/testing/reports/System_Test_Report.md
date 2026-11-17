# ElectroStock System Test Report

| Run detail | Value |
| --- | --- |
| Tested revision | `b37cbd9` plus the origin configuration fix and additional tests in this change |
| Run date | 17 November 2026 |
| Environment | Windows, FastAPI served by Uvicorn, PostgreSQL 17.11 with the project migrations, and the React/Vite development server |
| Test data | A temporary administrator and employee, a USB-C dock with a reorder threshold of four, and a sample supplier |
| Execution | Live HTTP requests to the running application. The browser smoke test used the same application and isolated database. |

## System test results

| ID | Requirements | Steps and test data | Expected result | Actual result | Status |
| --- | --- | --- | --- | --- | --- |
| ST-01 | ES-F-001, ES-F-002, ES-SR-001 | Sign in as admin with correct and incorrect passwords. Request the catalogue signed out. | Valid login succeeds. Invalid login and anonymous access are denied. | Valid login returned HTTP 200 with the admin role. Invalid login and anonymous access both returned 401. | Pass |
| ST-02 | ES-F-003, ES-SR-002 | Register and sign in as an employee. Try to open reports and create a product. | The account has the employee role. Both administrator operations are denied. | Signup returned 201 and sign-in returned 200. Both restricted operations returned 403. | Pass |
| ST-03 | ES-F-004 to ES-F-008 | Create a USB-C dock as admin, change its price to 125, then search and view it as an employee. Delete a separate sample product. | The revised product is found by search. The deleted item is unavailable. | The new price was returned, search and detail found the dock, and reading the deleted item returned 404. | Pass |
| ST-04 | ES-F-009 to ES-F-011, ES-F-016 | Try receiving five dock units as an employee. Receive five as admin, then sell two as employee. | Under the implemented role rule, employee receipt is denied. Stock goes from 0 to 5 to 3. | Employee receipt returned 403 and stock remained 0. Admin receipt increased stock to 5. Employee sale reduced stock to 3. See the requirements discrepancy below. | Pass against implemented role rule |
| ST-05 | ES-F-013, ES-NF-005 | Try to sell four units when only three are available. Read stock and transaction history again. | The sale is rejected and both records are unchanged. | The sale returned 400, stock stayed at three, and history remained at two transactions. | Pass |
| ST-06 | ES-F-014, ES-F-015 | Create a supplier as admin, update its phone number, then retrieve it as employee. | The employee can read the supplier and its revised phone number. | The employee retrieved the correct supplier name and updated phone number. | Pass |
| ST-07 | ES-F-012, ES-F-017 | Request the admin report after the dock reaches three units with a minimum of four. | The dock is listed as low stock. | The report listed the dock with three units and a minimum of four. | Pass |
| ST-08 | ES-F-018, ES-SR-005 | Retrieve audit history as admin and as employee after both accounts perform inventory actions. | The admin sees actors and timestamps. The employee is denied access. | The admin retrieved eight timestamped entries that included both actors. The employee received 403. | Pass |
| ST-09 | ES-NF-001 | Measure 30 sequential product searches for the dock on the small local catalogue. | At least 27 of 30 return the expected product in under three seconds. | 30 of 30 returned the expected product in under three seconds. The 90th percentile was 19.5 ms and the slowest request took 82.8 ms. | Pass on local sample |
| ST-10 | ES-F-001 | Open the browser app signed out, then sign in as the test administrator. | Sign-in opens the dashboard with live inventory data. | The dashboard identified the administrator and showed three units of the dock as low stock. | Pass |
| ST-11 | ES-NF-002 | Measure uptime over representative store operating hours and account for scheduled maintenance. | Availability meets the 99% target under the documented conditions. | The local test session did not cover a representative operating window. | Not run |
| ST-12 | ES-F-012, ES-F-015, ES-F-016, ES-F-017 | As admin, open Suppliers, Reports, and Transactions before the browser receipt. | The pages display the saved supplier, dock, and stock history. | The supplier directory showed the updated phone. Reports showed three units against a minimum of four. Transactions showed the five-unit receipt and two-unit sale. | Pass |
| ST-13 | ES-F-009, ES-F-010, ES-F-016 | As admin, record a receipt of two units in the browser, then open Inventory. | The receipt appears in history and stock rises from three to five. | The browser confirmed the receipt and displayed it in history. Inventory showed five units and an In stock status. | Pass |
| ST-14 | ES-F-003, ES-F-007, ES-SR-002 | Sign in as employee. Open the Reports URL, search Products for USB-C, then sign out. | Report data is restricted, the search returns the dock, and sign-out returns to sign-in. | The Reports page showed an administrator-access message. The search returned the dock with five units. Sign-out returned to the sign-in page. | Pass |

## Findings and scope

- Nine live API checks and four browser workflows passed under the tested conditions. The authorization, stock, and data integrity outcomes were verified against PostgreSQL. The search result describes the local sample catalogue.
- The SRS model assigns incoming stock to Employee/Admin. The API returned 403 for employee stock receipt. The team should resolve this discrepancy in the final SRS or implementation.
- The initial browser attempt was blocked because the backend read a different setting from the one documented in the example environment file. The fix uses the validated `FRONTEND_ORIGIN` and accepts `FRONTEND_URL` as a legacy fallback. The configured origin passed the preflight and the browser workflows passed on retest.
- This report records the checks executed in this run. It does not establish operational uptime, production performance, usability, or full security validation.

## Related evidence

- [Software Test Plan](../Software_Test_Plan.md)
- [Backend Unit Test Report](Unit_Test_Report.md)
- [Backend coverage export](backend-unit-coverage.xml)
