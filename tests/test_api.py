import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_convert_endpoint_happy_path() -> None:
    schema = {
        "format": "delimited",
        "fields": [
            {"name": "sku", "type": "string", "column": 0},
            {"name": "quantity", "type": "integer", "column": 1},
        ],
    }
    files = {"file": ("orders.csv", "ABC-123,4\nDEF-456,9\n", "text/csv")}
    response = client.post("/convert", data={"schema": json.dumps(schema)}, files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["records"] == [
        {"sku": "ABC-123", "quantity": 4},
        {"sku": "DEF-456", "quantity": 9},
    ]
    assert body["errors"] == []


def test_convert_endpoint_rejects_invalid_schema() -> None:
    files = {"file": ("orders.csv", "ABC-123,4\n", "text/csv")}
    response = client.post("/convert", data={"schema": "not json"}, files=files)
    assert response.status_code == 422


def test_convert_endpoint_reports_partial_errors() -> None:
    schema = {
        "format": "delimited",
        "fields": [
            {"name": "sku", "type": "string", "column": 0},
            {"name": "quantity", "type": "integer", "column": 1},
        ],
    }
    files = {"file": ("orders.csv", "ABC-123,4\nBAD,oops\n", "text/csv")}
    response = client.post("/convert", data={"schema": json.dumps(schema)}, files=files)

    assert response.status_code == 200
    body = response.json()
    assert len(body["records"]) == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["line_number"] == 2


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
