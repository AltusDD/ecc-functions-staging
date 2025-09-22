import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    collection = (req.route_params or {}).get("collection")
    # Minimal stub showing the collection name and empty items
    return func.HttpResponse(
        json.dumps({"collection": collection, "items": []}),
        mimetype="application/json",
        status_code=200
    )
