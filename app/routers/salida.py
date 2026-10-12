# app/routers/salida.py
from decimal import Decimal
from io import BytesIO

from pathlib import Path
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from datetime import datetime, timezone
from app.schemas.anulacion import AnulacionPeticion, AnulacionRespuesta

from app.models.catalogos import Producto

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_permission
from app.models import Bodega, Movimiento, MovimientoDetalle, ProductoPresentacion, Saldo, TipoMovimiento
from app.schemas.salida import SalidaCrear, SalidaListado, SalidaRespuesta

router = APIRouter(prefix="/salidas", tags=["Salidas"])
RUTA_LOGO = Path(__file__).resolve().parent.parent / "static" / "logohappycat.jpeg"

@router.get("/", response_model=list[SalidaListado], dependencies=[Depends(require_permission("inventario.ver"))])
def listar(db: Session = Depends(get_db)):
    consulta = (
        select(Movimiento, Bodega.nombre)
        .join(TipoMovimiento, TipoMovimiento.id == Movimiento.tipo_movimiento_id)
        .join(Bodega, Bodega.id == Movimiento.bodega_origen_id)
        .where(TipoMovimiento.nombre == "SALIDA_VENTA")
        .options(selectinload(Movimiento.detalles))
        .order_by(Movimiento.id.desc())
    )
    filas = db.execute(consulta).all()
    return [
        SalidaListado(
            id=mov.id,
            fecha=mov.fecha,
            bodega_nombre=nombre_bodega,
            productos=len(mov.detalles),
            estado=mov.estado,
            motivo_anulacion=mov.motivo_anulacion,
            fecha_anulacion=mov.fecha_anulacion,
        )
        for mov, nombre_bodega in filas
    ]


@router.post("/", response_model=SalidaRespuesta, status_code=201, dependencies=[Depends(require_permission("salida.crear"))])
def crear(datos: SalidaCrear, db: Session = Depends(get_db)):
    if db.get(Bodega, datos.bodega_id) is None:
        raise HTTPException(status_code=404, detail="La bodega no existe")

    tipo_salida = db.scalars(
        select(TipoMovimiento).where(TipoMovimiento.nombre == "SALIDA_VENTA")
    ).first()
    if tipo_salida is None:
        raise HTTPException(status_code=500, detail="Falta sembrar el tipo SALIDA_VENTA")

    # 1. Validar presentaciones y calcular cantidad_base, ANTES de tocar nada
    lineas_calculadas = []
    for linea in datos.detalles:
        presentacion = db.get(ProductoPresentacion, linea.presentacion_id)
        if presentacion is None:
            raise HTTPException(
                status_code=404,
                detail=f"La presentación {linea.presentacion_id} no existe",
            )
        cantidad_base = linea.cantidad * presentacion.factor
        lineas_calculadas.append((presentacion.producto_id, cantidad_base))

    # 2. Validar que haya saldo suficiente ANTES de restar nada
    for producto_id, cantidad_base in lineas_calculadas:
        saldo = db.get(Saldo, {"producto_id": producto_id, "bodega_id": datos.bodega_id})
        disponible = saldo.cantidad if saldo else Decimal("0")
        if disponible < cantidad_base:
            raise HTTPException(
                status_code=409,
                detail=f"No hay suficiente stock del producto {producto_id} "
                       f"(disponible: {disponible}, se pidió: {cantidad_base})",
            )

    # 3. Crear el movimiento
    movimiento = Movimiento(
        tipo_movimiento_id=tipo_salida.id,
        bodega_origen_id=datos.bodega_id,
        bodega_destino_id=None,
        compra_id=None,
    )
    movimiento.detalles = [
        MovimientoDetalle(producto_id=pid, cantidad=cant, costo_unitario=Decimal("0"))
        for pid, cant in lineas_calculadas
    ]
    db.add(movimiento)

    # 4. Restar el saldo
    for producto_id, cantidad_base in lineas_calculadas:
        saldo = db.get(Saldo, {"producto_id": producto_id, "bodega_id": datos.bodega_id})
        saldo.cantidad -= cantidad_base

    db.commit()
    db.refresh(movimiento)

    return SalidaRespuesta(
        movimiento_id=movimiento.id,
        bodega_id=datos.bodega_id,
        productos_afectados=len(lineas_calculadas),
    )
    
#Router para generar el PDF de la salida
@router.get("/{movimiento_id}/pdf", dependencies=[Depends(require_permission("inventario.ver"))])
def hoja_salida_pdf(movimiento_id: int, db: Session = Depends(get_db)):
    movimiento = db.get(Movimiento, movimiento_id)
    if movimiento is None:
        raise HTTPException(status_code=404, detail="La salida no existe")

    bodega = db.get(Bodega, movimiento.bodega_origen_id)
    detalles = db.scalars(
        select(MovimientoDetalle).where(MovimientoDetalle.movimiento_id == movimiento_id)
    ).all()

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("titulo", parent=estilos["Title"], alignment=2)  # 2 = a la derecha
    estilo_celda = estilos["Normal"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    # ---------- CABECERA: logo a la izquierda, título a la derecha ----------
    if RUTA_LOGO.exists():
        logo = Image(str(RUTA_LOGO), width=4 * cm, height=2 * cm, kind="proportional")
    else:
        logo = Paragraph("LOGO", estilo_celda)  # recuadro vacío mientras no tengas logo

    cabecera = Table(
        [[logo, Paragraph(f"HOJA DE SALIDA<br/>N.º {movimiento.id}", estilo_titulo)]],
        colWidths=[5 * cm, 12 * cm],
        rowHeights=[2.2 * cm],
    )
    if not RUTA_LOGO.exists():
        cabecera.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.5, colors.grey)]))

    # ---------- DATOS GENERALES ----------
    datos = Table(
        [
            ["Fecha:", f"{movimiento.fecha:%d/%m/%Y %H:%M}"],
            ["Bodega emisora:", bodega.nombre],
        ],
        colWidths=[4 * cm, 13 * cm],
    )
    datos.setStyle(TableStyle([("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))

    # ---------- TABLA DE DETALLE ----------
    filas = [["#", "Código", "Producto", "Categoría", "Cantidad", "Unidad"]]
    for i, d in enumerate(detalles, start=1):
        producto = db.get(Producto, d.producto_id)
        filas.append([
            i,
            producto.codigo,
            Paragraph(producto.nombre, estilo_celda),
            producto.categoria.nombre,
            f"{d.cantidad.normalize():f}",
            producto.unidad_base.abreviatura,
        ])

    tabla = Table(filas, colWidths=[1 * cm, 2.5 * cm, 6.5 * cm, 3 * cm, 2.2 * cm, 1.8 * cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6feb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    # ---------- FIRMAS ----------
    firmas = Table(
        [["______________________", "______________________"],
         ["Entregado por", "Recibido por"]],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    firmas.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))

    doc.build([
        cabecera, Spacer(1, 0.5 * cm),
        datos, Spacer(1, 0.7 * cm),
        tabla, Spacer(1, 2.5 * cm),
        firmas,
    ])
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="salida_{movimiento.id}.pdf"'},
    )
    
    
@router.patch("/{movimiento_id}/anular", response_model=AnulacionRespuesta, dependencies=[Depends(require_permission("salida.anular"))])
def anular(movimiento_id: int, datos: AnulacionPeticion, db: Session = Depends(get_db)):
    movimiento = db.get(Movimiento, movimiento_id, with_for_update=True)
    if movimiento is None:
        raise HTTPException(status_code=404, detail="La salida no existe")

    tipo = db.get(TipoMovimiento, movimiento.tipo_movimiento_id)
    if tipo is None or tipo.nombre != "SALIDA_VENTA":
        raise HTTPException(status_code=400, detail="Ese movimiento no es una salida")
    if movimiento.estado == "ANULADO":
        raise HTTPException(status_code=409, detail="La salida ya está anulada")

    bodega_id = movimiento.bodega_origen_id

    # Devolver al saldo lo que la salida había restado
    for linea in movimiento.detalles:
        saldo = db.get(
            Saldo,
            {"producto_id": linea.producto_id, "bodega_id": bodega_id},
            with_for_update=True,
        )
        if saldo is None:
            saldo = Saldo(
                producto_id=linea.producto_id,
                bodega_id=bodega_id,
                cantidad=Decimal("0"),
            )
            db.add(saldo)
        saldo.cantidad += linea.cantidad

    movimiento.estado = "ANULADO"
    movimiento.motivo_anulacion = datos.motivo
    movimiento.fecha_anulacion = datetime.now(timezone.utc)

    db.commit()
    return AnulacionRespuesta(
        id=movimiento.id,
        estado=movimiento.estado,
        motivo_anulacion=movimiento.motivo_anulacion,
        fecha_anulacion=movimiento.fecha_anulacion,
    )