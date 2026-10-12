#app\routers\presentacion.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_permission
from app.models import Producto, ProductoPresentacion, UnidadMedida
from app.schemas.presentacion import PresentacionCrear, PresentacionRespuesta

router = APIRouter(prefix="/presentaciones", tags=["Presentaciones"])


def _a_respuesta(presentacion: ProductoPresentacion) -> PresentacionRespuesta:
    return PresentacionRespuesta(
        id=presentacion.id,
        producto_id=presentacion.producto_id,
        unidad_id=presentacion.unidad_id,
        factor=presentacion.factor,
        precio_venta=presentacion.precio_venta,
        producto_nombre=presentacion.producto.nombre,
        unidad_nombre=presentacion.unidad.nombre,
        codigo_barras=presentacion.codigo_barras,
    )


@router.get("/", response_model=list[PresentacionRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(producto_id: int | None = None, db: Session = Depends(get_db)):
    consulta = select(ProductoPresentacion).options(
        selectinload(ProductoPresentacion.producto),
        selectinload(ProductoPresentacion.unidad),
    )
    if producto_id is not None:
        consulta = consulta.where(ProductoPresentacion.producto_id == producto_id)
    presentaciones = db.scalars(consulta.order_by(ProductoPresentacion.id)).all()
    return [_a_respuesta(p) for p in presentaciones]




@router.post("/", response_model=PresentacionRespuesta, status_code=201, dependencies=[Depends(require_permission("producto.gestionar"))])
def crear(datos: PresentacionCrear, db: Session = Depends(get_db)):
    if db.get(Producto, datos.producto_id) is None:
        raise HTTPException(status_code=404, detail="El producto no existe")
    if db.get(UnidadMedida, datos.unidad_id) is None:
        raise HTTPException(status_code=404, detail="La unidad no existe")

    repetida = db.scalars(
        select(ProductoPresentacion).where(
            ProductoPresentacion.producto_id == datos.producto_id,
            ProductoPresentacion.unidad_id == datos.unidad_id,
        )
    ).first()
    if repetida is not None:
        raise HTTPException(
            status_code=409,
            detail="Ese producto ya tiene una presentación en esa unidad",
        )

    presentacion = ProductoPresentacion(
        producto_id=datos.producto_id,
        unidad_id=datos.unidad_id,
        factor=datos.factor,
        precio_venta=datos.precio_venta,
    )
    db.add(presentacion)
    db.flush()
    presentacion.codigo_barras = f"PP{presentacion.id:08d}"
    db.commit()
    db.refresh(presentacion)
    return _a_respuesta(presentacion)