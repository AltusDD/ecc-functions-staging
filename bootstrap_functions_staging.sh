#!/usr/bin/env bash
set -euo pipefail

# ===== Config =====
APP_NAME="empirecommandcenter-altus-staging"             # Azure Function App name (existing)
BRANCH="stabilize-functions-staging"                     # Working branch
WORKFLOW_NAME="Deploy Functions (Staging)"
WORKFLOW_PATH=".github/workflows/deploy.yml"

# ===== Sanity checks =====
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not in a git repo. cd into your repo and re-run."; exit 1; }
mkdir -p .github/workflows

# ===== Files =====
mkdir -p ping legal_cases legal_export_cases portfolio

# host.json
cat > host.json <<'EOF'
{
  "version": "2.0",
  "extensionBundle": { "id": "Microsoft.Azure.Functions.ExtensionBundle", "version": "[4.*, 5.0.0)" }
}
EOF

# requirements.txt (minimal — azure-functions only)
cat > requirements.txt <<'EOF'
azure-functions>=1.20.0
EOF

# .gitignore
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.egg-info/

# Misc
.local/
.env
venv/
ENV/
env/
**/.DS_Store
EOF

# .funcignore
cat > .funcignore <<'EOF'
local.settings.json
.vscode/
.git/
.github/
tests/
EOF

# ping
cat > ping/function.json <<'EOF'
{
  "scriptFile": "__init__.py",
  "bindings": [
    { "authLevel":"anonymous","type":"httpTrigger","direction":"in","name":"req","methods":["get"],"route":"ping" },
    { "type":"http","direction":"out","name":"res" }
  ]
}
EOF
cat > ping/__init__.py <<'EOF'
import json, azure.functions as func
def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(json.dumps({"ok": True}), mimetype="application/json", status_code=200)
EOF

# legal_cases
cat > legal_cases/function.json <<'EOF'
{
  "scriptFile": "__init__.py",
  "bindings": [
    { "authLevel":"anonymous","type":"httpTrigger","direction":"in","name":"req","methods":["get"],"route":"legal/cases" },
    { "type":"http","direction":"out","name":"res" }
  ]
}
EOF
cat > legal_cases/__init__.py <<'EOF'
import azure.functions as func
def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("[]", mimetype="application/json", status_code=200)
EOF

# legal_export_cases
cat > legal_export_cases/function.json <<'EOF'
{
  "scriptFile": "__init__.py",
  "bindings": [
    { "authLevel":"anonymous","type":"httpTrigger","direction":"in","name":"req","methods":["get"],"route":"legal/export/cases" },
    { "type":"http","direction":"out","name":"res" }
  ]
}
EOF
cat > legal_export_cases/__init__.py <<'EOF'
import json, azure.functions as func
def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(json.dumps({"export":"cases","status":"ok"}), mimetype="application/json", status_code=200)
EOF

# portfolio
cat > portfolio/function.json <<'EOF'
{
  "scriptFile": "__init__.py",
  "bindings": [
    { "authLevel":"anonymous","type":"httpTrigger","direction":"in","name":"req","methods":["get"],"route":"portfolio/{collection}" },
    { "type":"http","direction":"out","name":"res" }
  ]
}
EOF
cat > portfolio/__init__.py <<'EOF'
import json, azure.functions as func
def main(req: func.HttpRequest) -> func.HttpResponse:
    collection = req.route_params.get("collection")
    return func.HttpResponse(json.dumps({"collection": collection, "items": []}), mimetype="application/json", status_code=200)
EOF

# README
cat > README.md <<'EOF'
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
EOF

# GitHub Actions workflow
cat > "$WORKFLOW_PATH" <<EOF
name: ${WORKFLOW_NAME}

on:
  push:
    branches: [ "main" ]

jobs:
  deploy:
    permissions:
      contents: read
      id-token: write
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Zip package
        run: zip -rq package.zip .

      - name: Deploy via Run-From-Package
        uses: azure/functions-action@v1
        with:
          app-name: ${APP_NAME}
          package: package.zip
          publish-profile: \${{ secrets.AZUREAPPSERVICE_PUBLISHPROFILE }}
EOF

# ===== Branch, commit, push =====
git fetch origin --quiet || true
if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  git checkout "$BRANCH"
else
  # base off main (or default branch)
  DEFAULT_BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
  git checkout -B "$BRANCH" "origin/${DEFAULT_BASE}" 2>/dev/null || git checkout -b "$BRANCH"
fi

git add .
git commit -m "Stabilize Functions staging: minimal HTTP stubs + workflow" || echo "Nothing to commit."
git push -u origin "$BRANCH"

# ===== Optionally set secret via gh =====
if command -v gh >/dev/null 2>&1; then
  if [[ -n "${PUBLISH_PROFILE_FILE:-}" && -f "${PUBLISH_PROFILE_FILE:-}" ]]; then
    echo "Setting repo secret AZUREAPPSERVICE_PUBLISHPROFILE from ${PUBLISH_PROFILE_FILE}"
    gh secret set AZUREAPPSERVICE_PUBLISHPROFILE < "${PUBLISH_PROFILE_FILE}"
  else
    echo "NOTE: To set the publish profile secret with gh, re-run with:"
    echo "      PUBLISH_PROFILE_FILE=./<your>.PublishSettings gh secret set AZUREAPPSERVICE_PUBLISHPROFILE < \$PUBLISH_PROFILE_FILE"
  fi

  # Create PR if none exists
  if ! gh pr view "$BRANCH" >/dev/null 2>&1; then
    gh pr create \
      --title "Stabilize Azure Functions staging: scaffolding + deploy workflow" \
      --body "Adds minimal HTTP stubs (ping, legal_cases, legal_export_cases, portfolio), host.json, ignores, and a GitHub Actions deploy workflow. Ensure repo secret AZUREAPPSERVICE_PUBLISHPROFILE is set with the publish profile XML to enable deployment." \
      --base main --head "$BRANCH" \
      || echo "Could not open PR automatically; open one in the GitHub UI."
  else
    echo "PR already exists for $BRANCH."
  fi
else
  echo "gh CLI not found. Push/PR done manually. Set the secret in GitHub → Settings → Secrets and variables → Actions:"
  echo "  Name: AZUREAPPSERVICE_PUBLISHPROFILE"
  echo "  Value: paste the publish profile XML for ${APP_NAME}"
  echo "Then open a PR from ${BRANCH} → main."
fi

echo "All set. After merge to main, the workflow will deploy to ${APP_NAME}."
echo "Smoke test (after deploy):"
echo "  curl -i https://${APP_NAME}.azurewebsites.net/api/ping"