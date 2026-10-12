#app\schemas\bodega.py
from pydantic import BaseModel, ConfigDict


class BodegaCrear(BaseModel):
    nombre: str
    direccion: str | None = None


class BodegaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    direccion: str | None