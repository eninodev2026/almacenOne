from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UsuarioSesion(BaseModel):
    id: int
    username: str
    nombre: str
    rol: str
    permisos: list[str]


class UsuarioCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(pattern=r"^[a-z0-9._-]{3,50}$")
    nombre: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    rol_id: int


class UsuarioEditar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    rol_id: int | None = None
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)


class UsuarioListado(BaseModel):
    id: int
    username: str
    nombre: str
    rol: str
    activo: bool


class RolListado(BaseModel):
    id: int
    nombre: str


class SesionActiva(BaseModel):
    id: int
    usuario_id: int
    username: str
    nombre: str
    rol: str
    inicio: datetime
    ultimo_uso: datetime
    ip: str | None