# app/routers/compra.py
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from datetime import datetime, timezone
from app.schemas.anulacion import AnulacionPeticion, AnulacionRespuesta

from app.database import get_db
from app.deps import require_permission
from app.models import (
    Bodega,
    Compra,
    CompraDetalle,
    Movimiento,
    MovimientoDetalle,
    Producto,
    ProductoPresentacion,
    Proveedor,
    Saldo,
    TipoMovimiento,
)
from app.schemas.compra import CompraCrear, CompraRespuesta, DTEImportarSchema

router = APIRouter(prefix="/compras", tags=["Compras"])

def _sumar_al_saldo(db, producto_id, bodega_id, cantidad, costo_unitario):
    saldo = db.get(Saldo, {"producto_id": producto_id, "bodega_id": bodega_id})
    if saldo is None:
        saldo = Saldo(
            producto_id=producto_id,
            bodega_id=bodega_id,
            cantidad=Decimal("0"),
            costo_promedio=Decimal("0"),
        )
        db.add(saldo)

    cantidad_actual = saldo.cantidad or Decimal("0")
    costo_actual = saldo.costo_promedio or Decimal("0")
    cantidad_nueva = cantidad_actual + cantidad

    if cantidad_nueva > 0:
        saldo.costo_promedio = (
            (cantidad_actual * costo_actual + cantidad * costo_unitario)
            / cantidad_nueva
        ).quantize(Decimal("0.0001"))
    saldo.cantidad = cantidad_nueva



@router.get("/", response_model=list[CompraRespuesta], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    consulta = select(Compra).options(selectinload(Compra.detalles)).order_by(Compra.id.desc())
    return db.scalars(consulta).all()


@router.post("/", response_model=CompraRespuesta, status_code=201, dependencies=[Depends(require_permission("compra.crear"))])
def crear(datos: CompraCrear, db: Session = Depends(get_db)):
    # 1. Validar que existan proveedor y bodega
    if db.get(Proveedor, datos.proveedor_id) is None:
        raise HTTPException(status_code=404, detail="El proveedor no existe")
    if db.get(Bodega, datos.bodega_id) is None:
        raise HTTPException(status_code=404, detail="La bodega no existe")

    tipo_ingreso = db.scalars(
        select(TipoMovimiento).where(TipoMovimiento.nombre == "INGRESO_COMPRA")
    ).first()
    if tipo_ingreso is None:
        raise HTTPException(
            status_code=500, detail="Falta sembrar el tipo INGRESO_COMPRA"
        )

    # 2. Armar la compra y sus líneas, calculando cantidad_base y totales
    compra = Compra(
        proveedor_id=datos.proveedor_id,
        numero_factura=datos.numero_factura,
        fecha_emision=datos.fecha_emision,
        fecha_compra=datos.fecha_compra,
        condicion_pago=datos.condicion_pago,
        observacion=datos.observacion,
        subtotal=Decimal("0"),
        descuento=Decimal("0"),
        iva=Decimal("0"),
        total=Decimal("0"),
    )

    subtotal = Decimal("0")
    descuento_total = Decimal("0")
    movimiento_lineas: list[MovimientoDetalle] = []

    for linea in datos.detalles:
        presentacion = db.get(ProductoPresentacion, linea.presentacion_id)
        if presentacion is None:
            raise HTTPException(
                status_code=404,
                detail=f"La presentación {linea.presentacion_id} no existe",
            )

        cantidad_base = linea.cantidad * presentacion.factor
        total_linea = (linea.cantidad * linea.precio_unitario) - linea.descuento
        costo_unitario_base = (linea.precio_unitario / presentacion.factor).quantize(
            Decimal("0.0001")
        )

        compra.detalles.append(
            CompraDetalle(
                presentacion_id=presentacion.id,
                cantidad=linea.cantidad,
                cantidad_base=cantidad_base,
                precio_unitario=linea.precio_unitario,
                descuento=linea.descuento,
                total_linea=total_linea,
                costo_unitario_base=costo_unitario_base,
            )
        )

        subtotal += linea.cantidad * linea.precio_unitario
        descuento_total += linea.descuento

        movimiento_lineas.append(
            MovimientoDetalle(
                producto_id=presentacion.producto_id,
                cantidad=cantidad_base,
                costo_unitario=costo_unitario_base,
            )
        )

    iva = ((subtotal - descuento_total) * Decimal("0.13")).quantize(Decimal("0.01"))
    compra.subtotal = subtotal
    compra.descuento = descuento_total
    compra.iva = iva
    compra.total = subtotal - descuento_total + iva

    db.add(compra)
    try:
        db.flush()  # asigna compra.id sin cerrar la transacción todavía
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esa factura ya fue registrada")

        # 3. Crear el movimiento de inventario ligado a esta compra
    movimiento = Movimiento(
        tipo_movimiento_id=tipo_ingreso.id,
        bodega_origen_id=None,
        bodega_destino_id=datos.bodega_id,
        compra_id=compra.id,
    )
    movimiento.detalles = movimiento_lineas
    db.add(movimiento)

    # 4. Subir el saldo y actualizar el costo promedio
    for linea_mov in movimiento_lineas:
        _sumar_al_saldo(
            db,
            linea_mov.producto_id,
            datos.bodega_id,
            linea_mov.cantidad,
            linea_mov.costo_unitario,
        )

    db.commit()
    db.refresh(compra)
    return compra


# ==============================================================================
# NUEVO ENDPOINT: IMPORTAR DESDE DTE (FACTURA ELECTRÓNICA)
# ==============================================================================

@router.post("/importar-dte", response_model=CompraRespuesta, status_code=201, dependencies=[Depends(require_permission("compra.crear"))])
def importar_desde_dte(datos: DTEImportarSchema, db: Session = Depends(get_db)):
    # 1. Validar bodega
    bodega = db.get(Bodega, datos.bodega_id)
    if bodega is None:
        raise HTTPException(status_code=404, detail="La bodega no existe")

    # 2. Buscar o Crear Proveedor automáticamente por NIT
    proveedor = db.scalar(select(Proveedor).where(Proveedor.nit == datos.nit_proveedor))
    if not proveedor:
        proveedor = Proveedor(
            nombre=datos.nombre_proveedor,
            nit=datos.nit_proveedor,
            nrc=datos.nrc_proveedor,
            telefono=datos.telefono_proveedor,
            correo=datos.correo_proveedor,
            direccion=datos.direccion_proveedor,
        )
        db.add(proveedor)
        db.flush()  # Para obtener el ID del proveedor recién creado

    # 3. Validar tipo de movimiento
    tipo_ingreso = db.scalar(select(TipoMovimiento).where(TipoMovimiento.nombre == "INGRESO_COMPRA"))
    if tipo_ingreso is None:
        raise HTTPException(status_code=500, detail="Falta sembrar el tipo INGRESO_COMPRA")

    # 4. Procesar detalles y mapear productos (Búsqueda inteligente)
    detalles_compra = []
    movimiento_lineas = []
    subtotal_calculado = Decimal("0")
    descuento_total = Decimal("0")
    descripciones_no_encontradas = []

    for linea in datos.detalles:
        # Búsqueda por nombre de producto o descripción de presentación (insensible a mayúsculas)
        presentacion = db.scalar(
            select(ProductoPresentacion).join(Producto).where(
                or_(
                    Producto.nombre.ilike(f"%{linea.descripcion}%"),
                    ProductoPresentacion.descripcion.ilike(f"%{linea.descripcion}%")
                )
            ).limit(1)
        )

        if not presentacion:
            descripciones_no_encontradas.append(linea.descripcion)
            continue

        # Cálculos basados en la lógica existente
        cantidad_base = linea.cantidad * presentacion.factor
        total_linea = (linea.cantidad * linea.precio_unitario) - linea.descuento
        costo_unitario_base = (linea.precio_unitario / presentacion.factor).quantize(Decimal("0.0001"))

        detalles_compra.append(
            CompraDetalle(
                presentacion_id=presentacion.id,
                cantidad=linea.cantidad,
                cantidad_base=cantidad_base,
                precio_unitario=linea.precio_unitario,
                descuento=linea.descuento,
                total_linea=total_linea,
                costo_unitario_base=costo_unitario_base,
            )
        )

        subtotal_calculado += linea.cantidad * linea.precio_unitario
        descuento_total += linea.descuento

        movimiento_lineas.append(
            MovimientoDetalle(
                producto_id=presentacion.producto_id,
                cantidad=cantidad_base,
                costo_unitario=costo_unitario_base,
            )
        )

    # 5. Si hubo productos que no se pudieron mapear, detenemos y avisamos al frontend
    if descripciones_no_encontradas:
        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": "No se pudieron mapear automáticamente algunos productos del DTE.",
                "descripciones_no_encontradas": descripciones_no_encontradas,
                "sugerencia": "Cree los productos en el sistema o ajuste las descripciones para que coincidan."
            }
        )

    # 6. Armar la Compra con cálculos propios para garantizar consistencia contable
    iva_calculado = ((subtotal_calculado - descuento_total) * Decimal("0.13")).quantize(Decimal("0.01"))
    total_calculado = subtotal_calculado - descuento_total + iva_calculado

    compra = Compra(
        proveedor_id=proveedor.id,
        numero_factura=datos.numero_factura,  # Usar numeroControl del DTE
        fecha_emision=datos.fecha_emision,
        fecha_compra=datos.fecha_emision,
        condicion_pago=datos.condicion_pago,
        observacion=datos.observacion,
        subtotal=subtotal_calculado,
        descuento=descuento_total,
        iva=iva_calculado,
        total=total_calculado,
        detalles=detalles_compra
    )

    db.add(compra)
    try:
        db.flush()  # asigna compra.id
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esa factura (número de control) ya fue registrada")

    # 7. Crear Movimiento de Inventario
    movimiento = Movimiento(
        tipo_movimiento_id=tipo_ingreso.id,
        bodega_origen_id=None,
        bodega_destino_id=datos.bodega_id,
        compra_id=compra.id,
        detalles=movimiento_lineas
    )
    db.add(movimiento)

    # 8. Actualizar saldos y costo promedio
    for linea_mov in movimiento_lineas:
        _sumar_al_saldo(
            db,
            linea_mov.producto_id,
            datos.bodega_id,
            linea_mov.cantidad,
            linea_mov.costo_unitario,
        )

    db.commit()
    db.refresh(compra)
    return compra

@router.patch("/{compra_id}/anular", response_model=AnulacionRespuesta, dependencies=[Depends(require_permission("stock.ajustar"))])
def anular(compra_id: int, datos: AnulacionPeticion, db: Session = Depends(get_db)):
    compra = db.get(Compra, compra_id, with_for_update=True)
    if compra is None:
        raise HTTPException(status_code=404, detail="La compra no existe")
    if compra.estado == "ANULADO":
        raise HTTPException(status_code=409, detail="La compra ya está anulada")

    movimiento = db.scalars(
        select(Movimiento).where(Movimiento.compra_id == compra_id)
    ).first()
    if movimiento is None:
        raise HTTPException(
            status_code=500, detail="La compra no tiene movimiento de inventario"
        )
    bodega_id = movimiento.bodega_destino_id

    # 1. Sumar lo que ingresó por producto (por si un producto viene en varias líneas)
    ingresado: dict[int, Decimal] = {}
    for linea in movimiento.detalles:
        ingresado[linea.producto_id] = (
            ingresado.get(linea.producto_id, Decimal("0")) + linea.cantidad
        )

    # 2. Validar que el saldo alcance ANTES de restar nada
    for producto_id, cantidad in ingresado.items():
        saldo = db.get(
            Saldo,
            {"producto_id": producto_id, "bodega_id": bodega_id},
            with_for_update=True,
        )
        disponible = saldo.cantidad if saldo else Decimal("0")
        if disponible < cantidad:
            producto = db.get(Producto, producto_id)
            raise HTTPException(
                status_code=409,
                detail=f"No se puede anular: de {producto.nombre} quedan {disponible} "
                       f"y esta compra ingresó {cantidad}. Ya se usó parte de esa mercadería.",
            )

    # 3. Restar el saldo
    for producto_id, cantidad in ingresado.items():
        saldo = db.get(Saldo, {"producto_id": producto_id, "bodega_id": bodega_id})
        saldo.cantidad -= cantidad

    # 4. Marcar compra y movimiento como anulados
    ahora = datetime.now(timezone.utc)
    for registro in (compra, movimiento):
        registro.estado = "ANULADO"
        registro.motivo_anulacion = datos.motivo
        registro.fecha_anulacion = ahora

    db.commit()
    return AnulacionRespuesta(
        id=compra.id,
        estado=compra.estado,
        motivo_anulacion=compra.motivo_anulacion,
        fecha_anulacion=compra.fecha_anulacion,
    )