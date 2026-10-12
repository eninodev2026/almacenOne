#app\models\catalogos.py
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Proveedor(Base):
    __tablename__ = "proveedor"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    nit: Mapped[str | None] = mapped_column(String(20))
    nrc: Mapped[str | None] = mapped_column(String(20))
    telefono: Mapped[str | None] = mapped_column(String(30))
    correo: Mapped[str | None] = mapped_column(String(100))
    direccion: Mapped[str | None] = mapped_column(String(255))


class Categoria(Base):
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class UnidadMedida(Base):
    __tablename__ = "unidad_medida"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    abreviatura: Mapped[str] = mapped_column(String(10))


class Bodega(Base):
    __tablename__ = "bodega"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    direccion: Mapped[str | None] = mapped_column(String(255))


class TipoMovimiento(Base):
    __tablename__ = "tipo_movimiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)


class Producto(Base):
    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria.id"))
    unidad_base_id: Mapped[int] = mapped_column(ForeignKey("unidad_medida.id"))
    
    categoria: Mapped["Categoria"] = relationship()
    unidad_base: Mapped["UnidadMedida"] = relationship()
    presentaciones: Mapped[list["ProductoPresentacion"]] = relationship(
        back_populates="producto"
    )
    


class ProductoPresentacion(Base):
    __tablename__ = "producto_presentacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"))
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad_medida.id"))
    factor: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    codigo_barras: Mapped[str | None] = mapped_column(String(50), unique=True)
    
    producto: Mapped["Producto"] = relationship(back_populates="presentaciones")
    unidad: Mapped["UnidadMedida"] = relationship()
    
    
    
    
    