#app\routers\proveedor.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models import Proveedor
from app.schemas.proveedor import ProveedorCrear, ProveedorRespuesta

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.get("/", response_model=list[ProveedorRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(Proveedor).order_by(Proveedor.nombre)).all()


@router.post("/", response_model=ProveedorRespuesta, status_code=201, dependencies=[Depends(require_permission("catalogo.gestionar"))])
def crear(datos: ProveedorCrear, db: Session = Depends(get_db)):
    proveedor = Proveedor(**datos.model_dump())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor