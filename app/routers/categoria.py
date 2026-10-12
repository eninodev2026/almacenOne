#app\routers\categoria.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models import Categoria
from app.schemas.categoria import CategoriaCrear, CategoriaRespuesta

router = APIRouter(prefix="/categorias", tags=["Categorías"])


@router.get("/", response_model=list[CategoriaRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(Categoria).order_by(Categoria.nombre)).all()


@router.post("/", response_model=CategoriaRespuesta, status_code=201, dependencies=[Depends(require_permission("catalogo.gestionar"))])
def crear(datos: CategoriaCrear, db: Session = Depends(get_db)):
    categoria = Categoria(nombre=datos.nombre)
    db.add(categoria)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esa categoría ya existe")
    db.refresh(categoria)
    return categoria