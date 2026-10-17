#app\models\usuario.py
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

roles_permisos = Table(
    "roles_permisos",
    Base.metadata,
    Column("rol_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permiso_id", ForeignKey("permisos.id", ondelete="CASCADE"), primary_key=True),
)


class Permiso(Base):
    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    descripcion: Mapped[str] = mapped_column(String(150), default="")


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    permisos: Mapped[list[Permiso]] = relationship(secondary=roles_permisos, lazy="selectin")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rol: Mapped[Rol] = relationship(lazy="joined")


class Sesion(Base):
    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_uso: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    usuario: Mapped[Usuario] = relationship(lazy="joined")


class BitacoraSeguridad(Base):
    __tablename__ = "bitacora_seguridad"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    username_intentado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evento: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[str] = mapped_column(String(255), default="")
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)