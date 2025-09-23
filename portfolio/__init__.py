import os
import json
import urllib.parse
from typing import Any, Dict, List
import azure.functions as func
import requests

# We use Supabase PostgREST directly—no extra libraries needed.
# Required App Settings (already present in your Function App):
#   SUPABASE_URL
#   SUPABASE_SERVICE_ROLE_KEY

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""

# Map the route segment to your Supabase table names
TABLES: Dict[str, str] = {
    "properties": "properties",
    "units": "units",
    "leases": "leases",
    "tenants": "tenants",
    "owners": "owners",
}

# For search (?q=), we build an OR ilike filter across relevant columns per table
SEARCH_COLUMNS: Dict[str, List[str]] = {
    "properties": ["name", "address1", "city", "state", "status"],
    "units": ["unitNumber", "status", "propertyId"],
    "leases": ["status", "unitId", "tenantId"],
    "tenants": ["name", "email", "phone"],
    "owners": ["name", "email", "phone"],
}

DEFAULT_LIMIT = 25
HTTP_TIMEOUT = 10  # seconds


def _error(msg: str, code: int = 500) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": msg}),
        mimetype="application/json",
        status_code=code,
    )


def _rest_get(table: str, limit: int, q: str | None) -> List[Dict[str, Any]]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase environment not configured (URL/key missing)")

    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Accept": "application/json",
        "Prefer": "count=exact",
    }

    params: Dict[str, str] = {"select": "*", "limit": str(max(1, limit))}
    # Simple ordering so results are deterministic
    params["order"] = "id.asc"

    if q:
        cols = SEARCH_COLUMNS.get(table, [])
        if cols:
            # PostgREST OR syntax: or=(col.ilike.*foo*,col2.ilike.*foo*)
            needle = f"*{q}*"
            or_parts = [f"{c}.ilike.{needle}" for c in cols]
            params["or"] = f"({','.join(or_parts)})"

    resp = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
    # Bubble up helpful error if PostgREST returns non-200
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Supabase REST error {resp.status_code}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except Exception as ex:
        raise RuntimeError(f"Invalid JSON from Supabase: {ex}")

    # Ensure array
    if isinstance(data, list):
        return data
    # Some PostgREST deployments might return an object with 'data'
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return data["data"]

    # Fallback: wrap single object
    return [data]


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        collection = (req.route_params.get("collection") or "").strip().lower()
        if collection not in TABLES:
            return _error(f"unknown collection '{collection}'", 404)

        # Parse limit
        try:
            limit = int(req.params.get("limit", str(DEFAULT_LIMIT)))
        except ValueError:
            limit = DEFAULT_LIMIT

        limit = max(1, min(limit, 500))  # guardrails

        # Parse q (search)
        q = req.params.get("q")
        if q:
            q = q.strip()
            if q == "":
                q = None

        table = TABLES[collection]
        items = _rest_get(table, limit, q)

        body = {
            "collection": collection,
            "items": items,
            # 'total' is optional; PostgREST count requires 'Prefer: count=exact' and reading headers.
            # Keeping response lean for now; UI only needs items.
        }
        return func.HttpResponse(json.dumps(body), mimetype="application/json", status_code=200)

    except Exception as ex:
        # Return a compact, actionable error without leaking secrets
        return _error(f"portfolio handler failed: {ex}", 500)
