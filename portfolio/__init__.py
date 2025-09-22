import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    collection = req.route_params.get("collection")
    return func.HttpResponse(
        json.dumps({"collection": collection, "items": []}),
        mimetype="application/json",
        status_code=200
    )