from pydantic import BaseModel, ConfigDict


class TipoMovimientoCrear(BaseModel):
    nombre: str


class TipoMovimientoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str