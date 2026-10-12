#app\routers\tipo_movimiento.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models import TipoMovimiento
from app.schemas.tipo_movimiento import TipoMovimientoCrear, TipoMovimientoRespuesta

router = APIRouter(prefix="/tipos-movimiento", tags=["Tipos de movimiento"])


@router.get("/", response_model=list[TipoMovimientoRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(TipoMovimiento).order_by(TipoMovimiento.id)).all()


@router.post("/", response_model=TipoMovimientoRespuesta, status_code=201, dependencies=[Depends(require_permission("catalogo.gestionar"))])
def crear(datos: TipoMovimientoCrear, db: Session = Depends(get_db)):
    tipo = TipoMovimiento(nombre=datos.nombre)
    db.add(tipo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese tipo ya existe")
    db.refresh(tipo)
    return tipo