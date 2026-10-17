#app\models\inventario.py   
from datetime import datetime
from decimal import Decimal
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.catalogos import Bodega

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class EstadoTraslado(str, enum.Enum):
    DESPACHADO = "DESPACHADO"
    RECIBIDO = "RECIBIDO"
    RECHAZADO = "RECHAZADO"
    ANULADO = "ANULADO"

class Movimiento(Base):
    __tablename__ = "movimiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_movimiento_id: Mapped[int] = mapped_column(ForeignKey("tipo_movimiento.id"))
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    bodega_origen_id: Mapped[int | None] = mapped_column(ForeignKey("bodega.id"))
    bodega_destino_id: Mapped[int | None] = mapped_column(ForeignKey("bodega.id"))
    compra_id: Mapped[int | None] = mapped_column(ForeignKey("compra.id"))
    estado: Mapped[str] = mapped_column(
        String(20), default="ACTIVO", server_default="ACTIVO"
    )
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    fecha_anulacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detalles: Mapped[list["MovimientoDetalle"]] = relationship()
    
    observacion_despacho: Mapped[str | None] = mapped_column(Text)
    observacion_recepcion: Mapped[str | None] = mapped_column(Text)
    fecha_recepcion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usuario_nombre: Mapped[str | None] = mapped_column(String(120))


class MovimientoDetalle(Base):
    __tablename__ = "movimiento_detalle"

    id: Mapped[int] = mapped_column(primary_key=True)
    movimiento_id: Mapped[int] = mapped_column(ForeignKey("movimiento.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 4))


class Saldo(Base):
    __tablename__ = "saldo"

    producto_id: Mapped[int] = mapped_column(
        ForeignKey("producto.id"), primary_key=True
    )
    bodega_id: Mapped[int] = mapped_column(
        ForeignKey("bodega.id"), primary_key=True
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    
    costo_promedio: Mapped[Decimal] = mapped_column(
    Numeric(12, 4), default=0, server_default="0"
    )

    bodega: Mapped["Bodega"] = relationship()