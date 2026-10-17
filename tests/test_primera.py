from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_la_documentacion_responde():
    respuesta = client.get("/docs")
    assert respuesta.status_code == 200