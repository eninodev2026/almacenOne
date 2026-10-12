#app\routers\stock.py
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_permission
from app.models import Producto, ProductoPresentacion, Saldo
from app.schemas.stock import PresentacionStock, SaldoBodega, StockProducto

router = APIRouter(prefix="/stock", tags=["Stock"])


@router.get("/", response_model=list[StockProducto], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    consulta = select(Producto).options(
        selectinload(Producto.categoria),
        selectinload(Producto.unidad_base),
        selectinload(Producto.presentaciones).selectinload(ProductoPresentacion.unidad),
    )
    productos = db.scalars(consulta.order_by(Producto.nombre)).all()

    resultado = []
    for producto in productos:
        saldos = db.scalars(
            select(Saldo)
            .where(Saldo.producto_id == producto.id)
            .options(selectinload(Saldo.bodega))
        ).all()

        resultado.append(
            StockProducto(
                producto_id=producto.id,
                codigo=producto.codigo,
                nombre=producto.nombre,
                categoria_nombre=producto.categoria.nombre,
                unidad_base_nombre=producto.unidad_base.nombre,
                presentaciones=[
                    PresentacionStock(
                        presentacion_id=p.id,
                        unidad_nombre=p.unidad.nombre,
                        factor=p.factor,
                        precio_venta=p.precio_venta,
                    )
                    for p in producto.presentaciones
                ],
                saldos=[
                    SaldoBodega(
                        bodega_id=s.bodega_id,
                        bodega_nombre=s.bodega.nombre,
                        cantidad_disponible=s.cantidad,
                    )
                    for s in saldos
                ],
                cantidad_total=sum((s.cantidad for s in saldos), Decimal("0")),
            )
        )

    return resultado