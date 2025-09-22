import json
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"export": "cases", "status": "ok"}),
        mimetype="application/json",
        status_code=200
    )
