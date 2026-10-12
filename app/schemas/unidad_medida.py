from pydantic import BaseModel, ConfigDict


class UnidadCrear(BaseModel):
    nombre: str
    abreviatura: str


class UnidadRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    abreviatura: str