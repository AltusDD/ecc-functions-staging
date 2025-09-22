import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Minimal stub returning an empty list
    return func.HttpResponse(
        json.dumps([]),
        mimetype="application/json",
        status_code=200
    )
