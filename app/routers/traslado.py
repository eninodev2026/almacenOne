
# app/routers/traslado.py
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.deps import require_permission
from app.models import Bodega, Movimiento, MovimientoDetalle, ProductoPresentacion, Saldo, TipoMovimiento
from app.models.inventario import EstadoTraslado
from app.schemas.traslado import ResolucionTraslado, TrasladoCrear, TrasladoRespuesta



import io
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import Response
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.catalogos import Producto
from app.models.usuario import Usuario


router = APIRouter(prefix="/traslados", tags=["Traslados"])


@router.post("/", response_model=TrasladoRespuesta, status_code=201, dependencies=[Depends(require_permission("salida.crear"))])
def crear(
    datos: TrasladoCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_permission("salida.crear")),
):
    if datos.bodega_origen_id == datos.bodega_destino_id:
        raise HTTPException(status_code=400, detail="La bodega de origen y la de destino no pueden ser la misma")
    if db.get(Bodega, datos.bodega_origen_id) is None:
        raise HTTPException(status_code=404, detail="La bodega de origen no existe")
    if db.get(Bodega, datos.bodega_destino_id) is None:
        raise HTTPException(status_code=404, detail="La bodega de destino no existe")

    tipo_traslado = db.scalars(
        select(TipoMovimiento).where(TipoMovimiento.nombre == "TRASLADO")
    ).first()
    if tipo_traslado is None:
        raise HTTPException(status_code=500, detail="Falta sembrar el tipo TRASLADO")

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

    # 2. Validar que haya saldo suficiente en el origen ANTES de mover nada
    for producto_id, cantidad_base in lineas_calculadas:
        saldo_origen = db.get(Saldo, {"producto_id": producto_id, "bodega_id": datos.bodega_origen_id})
        disponible = saldo_origen.cantidad if saldo_origen else Decimal("0")
        if disponible < cantidad_base:
            raise HTTPException(
                status_code=409,
                detail=f"No hay suficiente stock del producto {producto_id} "
                       f"(disponible: {disponible}, se pidió: {cantidad_base})",
            )

    # 3. Crear el movimiento con el costo promedio de la bodega origen
    movimiento = Movimiento(
        tipo_movimiento_id=tipo_traslado.id,
        bodega_origen_id=datos.bodega_origen_id,
        bodega_destino_id=datos.bodega_destino_id,
        compra_id=None,
        estado=EstadoTraslado.DESPACHADO.value,
        observacion_despacho=datos.observacion,
        usuario_nombre=usuario.nombre,
    )
    detalles = []
    for producto_id, cantidad_base in lineas_calculadas:
        saldo_origen = db.get(Saldo, {"producto_id": producto_id, "bodega_id": datos.bodega_origen_id})
        detalles.append(
            MovimientoDetalle(
                producto_id=producto_id,
                cantidad=cantidad_base,
                costo_unitario=saldo_origen.costo_promedio,
            )
        )
    movimiento.detalles = detalles
    db.add(movimiento)

    # 4. Restar del origen. El destino suma cuando confirme la recepción
    for producto_id, cantidad_base in lineas_calculadas:
        saldo_origen = db.get(Saldo, {"producto_id": producto_id, "bodega_id": datos.bodega_origen_id})
        saldo_origen.cantidad -= cantidad_base

    db.commit()
    db.refresh(movimiento)

    return TrasladoRespuesta(
        movimiento_id=movimiento.id,
        bodega_origen_id=datos.bodega_origen_id,
        bodega_destino_id=datos.bodega_destino_id,
        productos_afectados=len(lineas_calculadas),
        estado=movimiento.estado,
    )


def _sumar_saldo(db: Session, producto_id: int, bodega_id: int, cantidad: Decimal, costo: Decimal):
    """Suma stock a una bodega recalculando su costo promedio."""
    saldo = db.get(Saldo, {"producto_id": producto_id, "bodega_id": bodega_id})
    if saldo is None:
        db.add(Saldo(producto_id=producto_id, bodega_id=bodega_id,
                     cantidad=cantidad, costo_promedio=costo))
        return
    nueva_cantidad = saldo.cantidad + cantidad
    saldo.costo_promedio = (saldo.cantidad * saldo.costo_promedio + cantidad * costo) / nueva_cantidad
    saldo.cantidad = nueva_cantidad


def _traslado_despachado(db: Session, movimiento_id: int) -> Movimiento:
    """Busca el traslado (bloqueando la fila) y exige que siga DESPACHADO."""
    tipo = db.scalars(select(TipoMovimiento).where(TipoMovimiento.nombre == "TRASLADO")).first()
    movimiento = db.get(Movimiento, movimiento_id, with_for_update=True)
    if movimiento is None or tipo is None or movimiento.tipo_movimiento_id != tipo.id:
        raise HTTPException(status_code=404, detail="El traslado no existe")
    if movimiento.estado != EstadoTraslado.DESPACHADO.value:
        raise HTTPException(
            status_code=409,
            detail=f"El traslado ya está {movimiento.estado}; solo se puede resolver uno DESPACHADO",
        )
    return movimiento


@router.patch("/{movimiento_id}/recibir", dependencies=[Depends(require_permission("salida.crear"))])
def recibir(movimiento_id: int, datos: ResolucionTraslado, db: Session = Depends(get_db)):
    movimiento = _traslado_despachado(db, movimiento_id)
    for d in movimiento.detalles:
        _sumar_saldo(db, d.producto_id, movimiento.bodega_destino_id, d.cantidad, d.costo_unitario)

    movimiento.estado = EstadoTraslado.RECIBIDO.value
    movimiento.observacion_recepcion = datos.observacion
    movimiento.fecha_recepcion = datetime.now(timezone.utc)
    db.commit()
    return {"movimiento_id": movimiento.id, "estado": movimiento.estado}


@router.patch("/{movimiento_id}/rechazar", dependencies=[Depends(require_permission("salida.crear"))])
def rechazar(movimiento_id: int, datos: ResolucionTraslado, db: Session = Depends(get_db)):
    if not datos.observacion or not datos.observacion.strip():
        raise HTTPException(status_code=400, detail="Indica el motivo del rechazo en las observaciones")

    movimiento = _traslado_despachado(db, movimiento_id)
    # La mercadería rechazada vuelve a la bodega de origen
    for d in movimiento.detalles:
        _sumar_saldo(db, d.producto_id, movimiento.bodega_origen_id, d.cantidad, d.costo_unitario)

    movimiento.estado = EstadoTraslado.RECHAZADO.value
    movimiento.observacion_recepcion = datos.observacion.strip()
    movimiento.fecha_recepcion = datetime.now(timezone.utc)
    db.commit()
    return {"movimiento_id": movimiento.id, "estado": movimiento.estado}


@router.get("/", dependencies=[Depends(require_permission("inventario.ver"))])
def listar(
    estado: EstadoTraslado | None = Query(None),
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Reporte de traslados entre bodegas, del más reciente al más antiguo."""
    origen = aliased(Bodega)
    destino = aliased(Bodega)
    cantidad_productos = (
        select(func.count(MovimientoDetalle.id))
        .where(MovimientoDetalle.movimiento_id == Movimiento.id)
        .scalar_subquery()
    )
    consulta = (
        select(Movimiento, origen.nombre, destino.nombre, cantidad_productos)
        .select_from(Movimiento)
        .join(origen, origen.id == Movimiento.bodega_origen_id)
        .join(destino, destino.id == Movimiento.bodega_destino_id)
        .join(TipoMovimiento, TipoMovimiento.id == Movimiento.tipo_movimiento_id)
        .where(TipoMovimiento.nombre == "TRASLADO")
        .order_by(Movimiento.id.desc())
        .limit(limite)
    )
    if estado:
        consulta = consulta.where(Movimiento.estado == estado.value)

    return [
        {
            "id": m.id,
            "fecha": m.fecha.isoformat(),
            "estado": m.estado,
            "bodega_origen": nombre_origen,
            "bodega_destino": nombre_destino,
            "productos": total,
            "observacion_despacho": m.observacion_despacho,
            "observacion_recepcion": m.observacion_recepcion,
            "fecha_recepcion": m.fecha_recepcion.isoformat() if m.fecha_recepcion else None,
        }
        for m, nombre_origen, nombre_destino, total in db.execute(consulta).all()
    ]
    
    
    
# ================== COMPROBANTE PDF de TRASLADO entre bodegas ==================
_LOGO = Path(__file__).resolve().parents[1] / "static" / "logohappycat.jpeg"
_ZONA_SV = timezone(timedelta(hours=-6))  # El Salvador no usa horario de verano
_GRIS_OSCURO = colors.HexColor("#333333")
_GRIS_MEDIO = colors.HexColor("#777777")
_GRIS_CLARO = colors.HexColor("#E6E6E6")


def _p(texto, **kw):
    base = dict(fontName="Helvetica", fontSize=9, leading=11, textColor=_GRIS_OSCURO)
    base.update(kw)
    return Paragraph(escape(str(texto)), ParagraphStyle("x", **base))


def _generar_pdf_traslado(db: Session, mov: Movimiento) -> bytes:
    origen = db.get(Bodega, mov.bodega_origen_id)
    destino = db.get(Bodega, mov.bodega_destino_id)
    numero = f"T-{mov.id:06d}"
    fecha = mov.fecha.astimezone(_ZONA_SV)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.5 * cm, bottomMargin=1.8 * cm,
        title=f"Comprobante de traslado {numero}",
    )
    historia = []

    # Logo arriba a la izquierda
    if _LOGO.exists():
        ancho_px, alto_px = ImageReader(str(_LOGO)).getSize()
        ancho = 4.5 * cm
        logo = Image(str(_LOGO), width=ancho, height=ancho * alto_px / ancho_px)
        logo.hAlign = "LEFT"
        historia.append(logo)
    historia.append(Spacer(1, 0.4 * cm))

    # Título y número de comprobante
    historia.append(_p("COMPROBANTE DE TRASLADO ENTRE BODEGAS", fontName="Helvetica-Bold",
                       fontSize=15, leading=18, alignment=TA_CENTER, textColor=colors.black))
    historia.append(Spacer(1, 0.15 * cm))
    historia.append(_p(f"N.° de traslado: {numero}", fontName="Helvetica-Bold",
                       fontSize=12, leading=15, alignment=TA_CENTER))
    historia.append(Spacer(1, 0.4 * cm))

    # Datos de cabecera
    etiqueta = dict(fontName="Helvetica-Bold", fontSize=8, textColor=_GRIS_MEDIO)
    datos = [
        [_p("FECHA Y HORA", **etiqueta), _p("REGISTRADO POR", **etiqueta), _p("ESTADO", **etiqueta)],
        [_p(fecha.strftime("%d/%m/%Y  %H:%M:%S"), fontName="Helvetica-Bold"),
         _p(mov.usuario_nombre or "—", fontName="Helvetica-Bold"),
         _p(mov.estado, fontName="Helvetica-Bold")],
        [_p("BODEGA DE ORIGEN (SALE)", **etiqueta), _p("BODEGA DE DESTINO (RECIBE)", **etiqueta), ""],
        [_p(origen.nombre if origen else "—", fontName="Helvetica-Bold"),
         _p(destino.nombre if destino else "—", fontName="Helvetica-Bold"), ""],
    ]
    t_datos = Table(datos, colWidths=[5.6 * cm, 5.6 * cm, 5.8 * cm])
    t_datos.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, _GRIS_OSCURO),
        ("LINEBELOW", (0, 1), (-1, 1), 0.4, _GRIS_MEDIO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]))
    historia.append(t_datos)
    historia.append(Spacer(1, 0.5 * cm))

    # Detalle de mercadería
    cab = dict(fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.black)
    filas = [[_p("N.°", **cab), _p("CÓDIGO", **cab), _p("PRODUCTO", **cab), _p("UNIDAD", **cab),
              _p("CANTIDAD", alignment=TA_RIGHT, **cab), _p("COSTO UNIT.", alignment=TA_RIGHT, **cab),
              _p("TOTAL", alignment=TA_RIGHT, **cab)]]
    total_general = Decimal("0")
    for i, d in enumerate(mov.detalles, start=1):
        prod = db.get(Producto, d.producto_id)
        total_linea = d.cantidad * d.costo_unitario
        total_general += total_linea
        filas.append([
            _p(i), _p(prod.codigo if prod else "—"), _p(prod.nombre if prod else f"Producto {d.producto_id}"),
            _p(prod.unidad_base.abreviatura if prod else ""),
            _p(f"{d.cantidad:,.3f}", alignment=TA_RIGHT),
            _p(f"{d.costo_unitario:,.4f}", alignment=TA_RIGHT),
            _p(f"{total_linea:,.2f}", alignment=TA_RIGHT),
        ])
    filas.append(["", "", "", "", "",
                  _p("TOTAL", fontName="Helvetica-Bold", alignment=TA_RIGHT, textColor=colors.black),
                  _p(f"{total_general:,.2f}", fontName="Helvetica-Bold", alignment=TA_RIGHT, textColor=colors.black)])

    t_det = Table(filas, colWidths=[0.8 * cm, 2.6 * cm, 6.0 * cm, 1.6 * cm, 2.2 * cm, 1.9 * cm, 1.9 * cm],
                  repeatRows=1)
    t_det.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _GRIS_CLARO),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, _GRIS_OSCURO),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, _GRIS_OSCURO),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, colors.HexColor("#BBBBBB")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, _GRIS_OSCURO),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, _GRIS_OSCURO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    historia.append(t_det)

    if mov.observacion_despacho:
        historia.append(Spacer(1, 0.4 * cm))
        historia.append(_p("OBSERVACIONES DEL DESPACHO", fontName="Helvetica-Bold", fontSize=8, textColor=_GRIS_MEDIO))
        historia.append(_p(mov.observacion_despacho))

    # Firmas
    firmas = Table(
        [["", "", ""],
         [_p("FIRMA — ENTREGA", fontName="Helvetica-Bold", alignment=TA_CENTER), "",
          _p("FIRMA — RECIBE", fontName="Helvetica-Bold", alignment=TA_CENTER)],
         ["", "", ""],
         [_p("Nombre completo", alignment=TA_CENTER, textColor=_GRIS_MEDIO), "",
          _p("Nombre completo", alignment=TA_CENTER, textColor=_GRIS_MEDIO)]],
        colWidths=[7.0 * cm, 3.0 * cm, 7.0 * cm],
        rowHeights=[1.8 * cm, None, 1.3 * cm, None],
    )
    firmas.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.8, _GRIS_OSCURO), ("LINEABOVE", (2, 1), (2, 1), 0.8, _GRIS_OSCURO),
        ("LINEABOVE", (0, 3), (0, 3), 0.8, _GRIS_OSCURO), ("LINEABOVE", (2, 3), (2, 3), 0.8, _GRIS_OSCURO),
    ]))
    historia.append(Spacer(1, 1.2 * cm))
    historia.append(KeepTogether([firmas]))

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(_GRIS_MEDIO)
        canvas.drawString(1.8 * cm, 1.0 * cm, f"Comprobante {numero}  ·  Generado el "
                          f"{datetime.now(_ZONA_SV).strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(letter[0] - 1.8 * cm, 1.0 * cm, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return buffer.getvalue()


@router.get("/{movimiento_id}/pdf", dependencies=[Depends(require_permission("salida.crear"))])
def comprobante_pdf(movimiento_id: int, db: Session = Depends(get_db)):
    tipo = db.scalars(select(TipoMovimiento).where(TipoMovimiento.nombre == "TRASLADO")).first()
    movimiento = db.get(Movimiento, movimiento_id)
    if movimiento is None or tipo is None or movimiento.tipo_movimiento_id != tipo.id:
        raise HTTPException(status_code=404, detail="El traslado no existe")

    pdf = _generar_pdf_traslado(db, movimiento)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="traslado_{movimiento.id}.pdf"'},
    )    