from app.config import settings


def test_usa_la_base_de_pruebas():
    assert settings.database_url.endswith("/inventario_test")