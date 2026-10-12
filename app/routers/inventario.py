# app/routers/inventario.py
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models import Bodega, Compra, CompraDetalle, Movimiento, Producto, ProductoPresentacion, Saldo

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/", dependencies=[Depends(require_permission("inventario.ver"))])
def consultar_inventario(
    texto: str | None = Query(None),
    bodega_id: int | None = Query(None),
    stock_min: Decimal | None = Query(None),
    stock_max: Decimal | None = Query(None),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    dias_max: int | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        consulta = (
            select(
                Saldo.cantidad.label("stock"),
                Producto.nombre.label("producto_nombre"),
                Bodega.nombre.label("bodega_nombre"),
                Saldo.producto_id,
                Saldo.bodega_id,
            )
            .join(Producto, Saldo.producto_id == Producto.id)
            .join(Bodega, Saldo.bodega_id == Bodega.id)
        )

        if texto:
            consulta = consulta.where(Producto.nombre.ilike(f"%{texto}%"))
        if bodega_id:
            consulta = consulta.where(Saldo.bodega_id == bodega_id)
        if stock_min is not None:
            consulta = consulta.where(Saldo.cantidad >= stock_min)
        if stock_max is not None:
            consulta = consulta.where(Saldo.cantidad <= stock_max)

        resultados = db.execute(consulta).all()

        respuesta = []
        for row in resultados:
            # Buscar la fecha de la última compra ACTIVA que incluyó este producto en esta bodega
            ultima_fecha = db.scalar(
                select(func.max(Compra.fecha_compra))
                .join(Movimiento, Movimiento.compra_id == Compra.id)
                .join(CompraDetalle, CompraDetalle.compra_id == Compra.id)
                .join(ProductoPresentacion, ProductoPresentacion.id == CompraDetalle.presentacion_id)
                .where(and_(
                    Compra.estado == "ACTIVO",
                    Movimiento.bodega_destino_id == row.bodega_id,
                    ProductoPresentacion.producto_id == row.producto_id
                ))
            )

            dias_bodega = (date.today() - ultima_fecha).days if ultima_fecha else 0

            if dias_max is not None and dias_bodega > dias_max:
                continue
            if fecha_desde and (not ultima_fecha or ultima_fecha < fecha_desde):
                continue
            if fecha_hasta and (not ultima_fecha or ultima_fecha > fecha_hasta):
                continue

            # Calcular costo promedio desde CompraDetalle de compras ACTIVAS
            costo_unitario = db.scalar(
                select(func.avg(CompraDetalle.costo_unitario_base))
                .join(Compra, Compra.id == CompraDetalle.compra_id)
                .join(ProductoPresentacion, ProductoPresentacion.id == CompraDetalle.presentacion_id)
                .where(and_(
                    Compra.estado == "ACTIVO",
                    ProductoPresentacion.producto_id == row.producto_id
                ))
            ) or Decimal("0")

            stock_val = float(row.stock) if row.stock else 0.0
            costo_val = float(costo_unitario) if costo_unitario else 0.0

            respuesta.append({
                "producto_nombre": row.producto_nombre,
                "presentacion_nombre": "Unidad",
                "bodega_nombre": row.bodega_nombre,
                "stock": stock_val,
                "costo_unitario": costo_val,
                "valor_total": stock_val * costo_val,
                "dias_bodega": dias_bodega,
                "ultima_movimentacion": ultima_fecha.isoformat() if ultima_fecha else None,
            })

        return respuesta
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))