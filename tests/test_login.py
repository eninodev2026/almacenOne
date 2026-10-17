from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_correcto(usuario_admin):
    respuesta = client.post("/auth/login", json=usuario_admin)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["username"] == "admin_test"
    assert "catalogo.gestionar" in datos["permisos"]


def test_login_con_contrasena_incorrecta(usuario_admin):
    respuesta = client.post(
        "/auth/login",
        json={"username": "admin_test", "password": "mala"},
    )
    assert respuesta.status_code == 401