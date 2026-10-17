from sqlalchemy import select

from app.database import SessionLocal
from app.models import Bodega


def test_guardar_y_leer_una_bodega():
    db = SessionLocal()
    try:
        # 1. Guardamos una bodega
        db.add(Bodega(nombre="Bodega de prueba", direccion="Calle 1"))
        db.flush()

        # 2. La buscamos de vuelta
        consulta = select(Bodega).where(Bodega.nombre == "Bodega de prueba")
        encontrada = db.scalars(consulta).first()

        # 3. Revisamos que sea la que guardamos
        assert encontrada is not None
        assert encontrada.direccion == "Calle 1"
    finally:
        # Deshacemos todo: la base queda limpia
        db.rollback()
        db.close()