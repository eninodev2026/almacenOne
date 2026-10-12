#app\routers\unidad_medida.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models import UnidadMedida
from app.schemas.unidad_medida import UnidadCrear, UnidadRespuesta

router = APIRouter(prefix="/unidades", tags=["Unidades de medida"])


@router.get("/", response_model=list[UnidadRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(UnidadMedida).order_by(UnidadMedida.nombre)).all()


@router.post("/", response_model=UnidadRespuesta, status_code=201, dependencies=[Depends(require_permission("catalogo.gestionar"))])
def crear(datos: UnidadCrear, db: Session = Depends(get_db)):
    unidad = UnidadMedida(nombre=datos.nombre, abreviatura=datos.abreviatura)
    db.add(unidad)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esa unidad ya existe")
    db.refresh(unidad)
    return unidad