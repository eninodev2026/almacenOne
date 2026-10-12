#app\routers\bodega.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models import Bodega
from app.schemas.bodega import BodegaCrear, BodegaRespuesta

router = APIRouter(prefix="/bodegas", tags=["Bodegas"])


@router.get("/", response_model=list[BodegaRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(Bodega).order_by(Bodega.nombre)).all()


@router.post("/", response_model=BodegaRespuesta, status_code=201, dependencies=[Depends(require_permission("catalogo.gestionar"))])
def crear(datos: BodegaCrear, db: Session = Depends(get_db)):
    bodega = Bodega(**datos.model_dump())
    db.add(bodega)
    db.commit()
    db.refresh(bodega)
    return bodega