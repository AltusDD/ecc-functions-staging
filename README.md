# ECC Functions (Staging)

Staging Azure Functions app for Empire Command Center (ECC). Python (3.11) on Functions v4.

## Endpoints
- `GET /api/ping` → `{"ok": true}`
- `GET /api/legal/cases` → `[]`
- `GET /api/legal/export/cases` → `{"export":"cases","status":"ok"}`
- `GET /api/portfolio/{collection}` → `{"collection":"...", "items":[]}`

## Deploy
This repo deploys via GitHub Actions using the Azure publish profile secret:
- Secret name: `AZUREAPPSERVICE_PUBLISHPROFILE`
- Value: contents of the Function App publish profile XML

Push to `main` triggers deployment.
