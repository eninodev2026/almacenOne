#app\routers\producto.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_permission
from app.models import Categoria, Producto, UnidadMedida
from app.schemas.producto import ProductoCrear, ProductoRespuesta
from sqlalchemy import or_, select
from app.schemas.producto import ProductoCrear, ProductoEditar, ProductoLista, ProductoRespuesta

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("/", response_model=list[ProductoRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(Producto).order_by(Producto.nombre)).all()

@router.get("/buscar", response_model=list[ProductoRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def buscar(q: str = "", limite: int = 10, db: Session = Depends(get_db)):
    consulta = select(Producto)
    for palabra in q.split():
        patron = f"%{palabra}%"
        consulta = consulta.where(
            or_(Producto.nombre.ilike(patron), Producto.codigo.ilike(patron))
        )
    consulta = consulta.order_by(Producto.nombre).limit(min(limite, 50))
    return db.scalars(consulta).all()


@router.post("/", response_model=ProductoRespuesta, status_code=201, dependencies=[Depends(require_permission("producto.gestionar"))])
def crear(datos: ProductoCrear, db: Session = Depends(get_db)):
    if db.get(Categoria, datos.categoria_id) is None:
        raise HTTPException(status_code=404, detail="La categoría no existe")
    if db.get(UnidadMedida, datos.unidad_base_id) is None:
        raise HTTPException(status_code=404, detail="La unidad base no existe")

    producto = Producto(
        codigo=datos.codigo,
        nombre=datos.nombre,
        categoria_id=datos.categoria_id,
        unidad_base_id=datos.unidad_base_id,
    )
    db.add(producto)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese código de producto ya existe")
    db.refresh(producto)
    return producto


@router.put("/{producto_id}", response_model=ProductoRespuesta, dependencies=[Depends(require_permission("producto.gestionar"))])
def editar(producto_id: int, datos: ProductoEditar, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="El producto no existe")
    if db.get(Categoria, datos.categoria_id) is None:
        raise HTTPException(status_code=404, detail="La categoría no existe")
    if db.get(UnidadMedida, datos.unidad_base_id) is None:
        raise HTTPException(status_code=404, detail="La unidad base no existe")

    producto.codigo = datos.codigo
    producto.nombre = datos.nombre
    producto.categoria_id = datos.categoria_id
    producto.unidad_base_id = datos.unidad_base_id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese código de producto ya existe")
    db.refresh(producto)
    return producto


@router.get("/lista", response_model=list[ProductoLista], dependencies=[Depends(require_permission("inventario.ver"))])
def listar_con_nombres(db: Session = Depends(get_db)):
    productos = db.scalars(
        select(Producto)
        .options(joinedload(Producto.categoria), joinedload(Producto.unidad_base))
        .order_by(Producto.nombre)
    ).all()
    return [
        ProductoLista(
            id=p.id,
            codigo=p.codigo,
            nombre=p.nombre,
            categoria_id=p.categoria_id,
            unidad_base_id=p.unidad_base_id,
            categoria_nombre=p.categoria.nombre,
            unidad_base_nombre=p.unidad_base.nombre,
        )
        for p in productos
    ]