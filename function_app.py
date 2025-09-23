import json
import azure.functions as func


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="ping", methods=["GET"])
def ping(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"ok": True}),
        mimetype="application/json",
        status_code=200,
    )


@app.route(route="legal/export/cases", methods=["GET"])
def legal_export_cases(req: func.HttpRequest) -> func.HttpResponse:
    # You can read query params like: since = req.params.get("since")
    payload = {"export": "cases", "status": "ok"}
    return func.HttpResponse(
        json.dumps(payload),
        mimetype="application/json",
        status_code=200,
    )


@app.route(route="portfolio/{collection}", methods=["GET"])
def portfolio(req: func.HttpRequest) -> func.HttpResponse:
    collection = req.route_params.get("collection") or "unknown"
    # Return an empty list for now so the UI gets 200 and parses fine
    payload = {"collection": collection, "items": []}
    return func.HttpResponse(
        json.dumps(payload),
        mimetype="application/json",
        status_code=200,
    )
