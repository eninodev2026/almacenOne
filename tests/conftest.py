import os
from pathlib import Path
import pytest
from dotenv import dotenv_values

# Leemos tu .env solo para sacar la dirección de la base real
ruta_env = Path(__file__).resolve().parent.parent / ".env"
valores = {k.lower(): v for k, v in dotenv_values(ruta_env).items()}
url_real = valores["database_url"]

# Cambiamos el nombre de la base al final: inventario -> inventario_test
url_test = url_real.rsplit("/", 1)[0] + "/inventario_test"

# Esto tiene prioridad sobre el .env
os.environ["DATABASE_URL"] = url_test


@pytest.fixture(scope="session", autouse=True)
def crear_tablas():
    from app.database import Base, engine
    import app.models  # carga todos los modelos

    # Seguro: si por error no es la base de pruebas, se detiene
    assert str(engine.url).endswith("/inventario_test")

    Base.metadata.create_all(engine)
    
    
from sqlalchemy import text


@pytest.fixture(scope="session")
def usuario_admin():
    from app.database import SessionLocal, engine
    from app.models.usuario import Permiso, Rol, Usuario
    from app.security import hash_password

    assert str(engine.url).endswith("/inventario_test")

    tablas = "roles_permisos, permisos, roles, usuarios, sesiones, bitacora_seguridad"
    limpiar = text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE")

    db = SessionLocal()
    db.execute(limpiar)
    db.commit()

    permisos = [
        Permiso(codigo="inventario.ver", descripcion="Ver inventario"),
        Permiso(codigo="catalogo.gestionar", descripcion="Gestionar catálogos"),
    ]
    rol = Rol(nombre="admin_test", permisos=permisos)
    db.add(Usuario(
        username="admin_test",
        nombre="Admin de Prueba",
        password_hash=hash_password("Prueba123!"),
        rol=rol,
    ))
    db.commit()
    db.close()

    yield {"username": "admin_test", "password": "Prueba123!"}

    db = SessionLocal()
    db.execute(limpiar)
    db.commit()
    db.close()    