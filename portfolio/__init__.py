# portfolio/__init__.py
import os
import json
import urllib.parse
import requests
import azure.functions as func

# -------- Config (env-driven) --------
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")

# Map the five collections to your real tables.
# If your physical table names differ, change them here (only here).
TABLES = {
    "properties": "properties",
    "units": "units",
    "leases": "leases",
    "tenants": "tenants",
    "owners": "owners",
}

# Columns used for free-text search per collection.
# Adjust to your real column names (snake_case typical with Supabase).
SEARCH_COLUMNS = {
    "properties": ["name", "address", "city", "state", "zip"],
    "units": ["unit_number", "property_id"],
    "leases": ["id", "unit_id", "status"],
    "tenants": ["name", "email", "phone"],
    "owners": ["name", "email", "phone"],
}

def _bad_request(msg: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": msg}),
        status_code=400,
        mimetype="application/json",
    )

def _server_error(msg: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": msg}),
        status_code=500,
        mimetype="application/json",
    )

def _headers():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY app settings")
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Accept-Profile": SCHEMA,
        "Content-Profile": SCHEMA,
        # Ask PostgREST to include total in Content-Range
        "Prefer": "count=exact",
    }

def _build_or_filter(cols, q):
    # or=(col.ilike.*q*,col2.ilike.*q*)
    if not q:
        return None
    needle = f"*{q}*"
    parts = [f'{c}.ilike.{needle}' for c in cols]
    joined = ",".join(parts)
    return f"or=({joined})"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        collection = (req.route_params.get("collection") or "").strip().lower()
        if collection not in TABLES:
            return _bad_request(f"Unknown collection '{collection}'. Valid: {', '.join(TABLES)}")

        table = TABLES[collection]
        q = (req.params.get("q") or "").strip()
        limit = int(req.params.get("limit") or 25)
        offset = int(req.params.get("offset") or 0)
        order = req.params.get("order") or "id.asc"
        debug = req.params.get("debug") == "1"
        select = req.params.get("select") or "*"

        url = f"{SUPABASE_URL}/rest/v1/{urllib.parse.quote(table)}"
        params = {
            "select": select,
            "limit": str(max(1, min(limit, 500))),
            "offset": str(max(0, offset)),
            "order": order,
        }

        or_filter = _build_or_filter(SEARCH_COLUMNS.get(collection, []), q)
        if or_filter:
            # ‘or’ must be top-level param, keep as-is (no extra quoting)
            # requests will percent-encode parentheses, which PostgREST supports
            params["or"] = f"({','.join([f'{c}.ilike.*{q}*' for c in SEARCH_COLUMNS[collection]])})"  # safety, duplicates above builder

        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        # Raise for HTTP errors (404 means table missing/typo)
        if r.status_code >= 400:
            return _server_error(f"Supabase error {r.status_code}: {r.text}")

        items = r.json()
        # Total from Content-Range: e.g. "0-24/137"
        total = None
        cr = r.headers.get("Content-Range")
        if cr and "/" in cr:
            try:
                total = int(cr.split("/", 1)[1])
            except Exception:
                total = None

        payload = {"collection": collection, "items": items, "total": total}
        if debug:
            payload["_debug"] = {
                "url": r.url,
                "status": r.status_code,
                "content_range": r.headers.get("Content-Range"),
                "schema": SCHEMA,
            }

        return func.HttpResponse(
            json.dumps(payload, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        return _server_error(str(e))
