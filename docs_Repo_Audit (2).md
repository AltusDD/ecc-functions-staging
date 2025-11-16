# Repo Audit: AltusDD/ecc-functions-staging

## 1. Summary
- Purpose (one sentence): A staging Azure Functions app prototype for ECC that exposes minimal HTTP endpoints and an experimental Supabase-backed portfolio query.
- System ownership: Empire Command Center (ECC) (inferred from Azure Function App name `empirecommandcenter-altus-staging` in the deployment workflow).
- Tech stack: Python 3.11, Azure Functions (Python v2 programming model via `FunctionApp` decorators), `requests` for outbound HTTP, Supabase REST (PostgREST) access.

## 2. Deploy & Runtime

### Azure Functions Present
Implemented using the Python v2 model (`FunctionApp` in `function_app.py`):

| Function Name | Trigger Type | Auth Level | HTTP Methods | Route (defined) | Effective URL (Azure default adds `/api/`) |
|---------------|--------------|-----------|--------------|-----------------|-------------------------------------------|
| ping | HTTP | Anonymous | GET | ping | /api/ping |
| legal_export_cases | HTTP | Anonymous | GET | legal/export/cases | /api/legal/export/cases |
| portfolio | HTTP | Anonymous | GET | portfolio/{collection} | /api/portfolio/{collection} |

Notes:
- All are pure HTTP triggers returning JSON.
- No Timer, Queue, Blob, ServiceBus, or other bindings are present.
- `portfolio/__init__.py` contains a `main(req)` function that looks like an older (function.json) style entry point, but the current routing in `function_app.py` does NOT call it yet; instead the deployed route returns a placeholder payload. The earlier commit text refers to per-function folders (e.g. `ping/function.json`), but those are no longer present in the current tree—indicating a migration to the new model.

### GitHub Actions Workflow
Workflow file: `.github/workflows/deploy-functions.yml`

Key points:
- Triggers: push to `main`, and manual dispatch.
- Deploys to Azure Function App named: `empirecommandcenter-altus-staging`
- Resource group: `empirecommandcenter-altus-staging_group`
- Sets runtime/app settings (remote build pattern):
  - `FUNCTIONS_WORKER_RUNTIME=python`
  - `FUNCTIONS_EXTENSION_VERSION=~4`
  - `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
  - `ENABLE_ORYX_BUILD=true`
- Python version pinned by env: `PYTHON_VERSION=3.11`
- Uses OIDC login with secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- Performs simple smoke tests against:
  - `/api/ping`
  - `/api/legal/export/cases`
  - `/api/portfolio/properties`

### Environment Variables / Settings Expected by Code
From `portfolio/__init__.py`:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_SCHEMA` (defaults to `public` if unset)

From the workflow / deployment flow:
- `AZURE_FUNCTIONAPP_NAME`
- `AZURE_RESOURCE_GROUP`
- `PYTHON_VERSION`
- (Azure app settings applied during deploy as above)
- Secrets needed for auth: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`

## 3. Data & Schema

### Supabase / Postgres Usage
The only data-access logic is in `portfolio/__init__.py`, constructing REST queries to Supabase (PostgREST):

Tables referenced (via `TABLES` mapping):
- `properties`
- `units`
- `leases`
- `tenants`
- `owners`

Search columns (used to build an `or=...ilike...` filter):
- properties: name, address, city, state, zip
- units: unit_number, property_id
- leases: id, unit_id, status
- tenants: name, email, phone
- owners: name, email, phone

Assumptions about IDs:
- Defaults `order` to `id.asc` implying each table has an `id` column (likely integer). No evidence of prefixed text IDs (e.g. `pr_`, `un_`)—the code treats them generically and casts none.
- Foreign key style names (`property_id`, `unit_id`) also suggest integer FK posture typical of normalized schemas.

Pagination & metadata:
- `limit`, `offset`, `order` query params expected.
- Extracts total count from `Content-Range` header (PostgREST convention).

### DoorLoop
No references or calls to DoorLoop APIs appear in the retrieved code. No legacy schema artifacts tied to DoorLoop naming were found.

## 4. Freshness Check

Most recent code commit (not just README) affecting runtime/dependencies:
- Commit: `f60aa03c6f793a06a2004544a85eaca46f8e6302`
- Date: 2025-09-23
- Message: “Add requests package to requirements”

Recent earlier commits the same day refined Supabase integration and routes:
- “Refactor Supabase config and request handling”
- Added initial portfolio module.

Architecture alignment:
- Uses Supabase REST directly and the new Azure Functions Python decorator model.
- This appears to be a newer staging experiment rather than legacy ECC backend patterns (no monolithic service layer or older function.json structure except a remnant module).
- The `portfolio` route served to clients is still stubbed (does not yet return Supabase data), meaning the integration is only partially wired.

## 5. Decision Suggestion

Recommended status: **PLAYGROUND**

Rationale:
- Minimal business logic: three simple endpoints; only one (portfolio) has a more advanced data module, and that module is not yet invoked by the deployed route.
- Active experimentation indicators: repository name includes “staging”; recent refactors; migration from old per-folder model to new FunctionApp decorators mid-commit history.
- Not enough integrated or production-critical functionality to classify as ACTIVE.
- Too recent and experimental to mark as LEGACY (it is not historical; it is a prototype in progress).
  
If production use is desired, wiring `portfolio` route to the Supabase logic and adding auth, error taxonomy, and test coverage would be required first.

## 6. Archival Considerations

If this repo were to be archived, copy or port the following before doing so:
- `portfolio/__init__.py`: Supabase query pattern (search, pagination, total extraction from `Content-Range`).
- `.github/workflows/deploy-functions.yml`: OIDC-based Azure Functions deployment workflow template.
- `function_app.py`: Example of Python v2 FunctionApp decorator usage and route structure.
- `requirements.txt`: Baseline dependencies (at least `azure-functions` and `requests`).
- Any environment variable naming conventions (`SUPABASE_*`) to maintain consistency across repos.

Missing / To Confirm Before Archiving:
- Decide whether to actually use the richer Supabase logic (wire it into the `portfolio` route) elsewhere.
- Ensure secrets and app settings are documented in a secure location (Azure portal / infra docs).

---

## Consolidated Snapshot

| Aspect | Key Points |
|--------|------------|
| Purpose | Staging prototype for ECC HTTP endpoints + Supabase portfolio exploration |
| Functions | 3 HTTP (ping, legal/export/cases, portfolio/{collection}) |
| Data Access | Supabase REST for 5 portfolio-related tables (properties, units, leases, tenants, owners) |
| External APIs | Only Supabase; no DoorLoop calls |
| Freshness | Active edits on 2025-09-23; experimental wiring not complete |
| Recommended Status | PLAYGROUND |
| Critical Artifacts to Preserve | Supabase query module, deployment workflow, FunctionApp pattern |

## Final Recommendation

Treat this repo as a PLAYGROUND staging sandbox. Do not rely on it for production data access until the portfolio route actually returns Supabase data and basic operational concerns (auth, validation, observability) are addressed.
