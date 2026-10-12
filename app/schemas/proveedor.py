#app\schemas\proveedor.py
from pydantic import BaseModel, ConfigDict


class ProveedorCrear(BaseModel):
    nombre: str
    nit: str | None = None
    nrc: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None


class ProveedorRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nit: str | None
    nrc: str | None
    telefono: str | None
    correo: str | None
    direccion: str | None