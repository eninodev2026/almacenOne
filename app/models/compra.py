from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Compra(Base):
    __tablename__ = "compra"
    __table_args__ = (
        Index(
            "uq_compra_proveedor_factura_activa",
            "proveedor_id",
            "numero_factura",
            unique=True,
            postgresql_where=text("estado = 'ACTIVO'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id"))
    numero_factura: Mapped[str] = mapped_column(String(50))
    fecha_emision: Mapped[date] = mapped_column(Date)
    fecha_compra: Mapped[date] = mapped_column(Date)
    condicion_pago: Mapped[str] = mapped_column(String(20))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    iva: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    observacion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(
        String(20), default="ACTIVO", server_default="ACTIVO"
    )
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    fecha_anulacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    detalles: Mapped[list["CompraDetalle"]] = relationship(
        back_populates="compra", cascade="all, delete-orphan"
    )


class CompraDetalle(Base):
    __tablename__ = "compra_detalle"

    id: Mapped[int] = mapped_column(primary_key=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compra.id"))
    presentacion_id: Mapped[int] = mapped_column(ForeignKey("producto_presentacion.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    cantidad_base: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_linea: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    costo_unitario_base: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    compra: Mapped["Compra"] = relationship(back_populates="detalles")