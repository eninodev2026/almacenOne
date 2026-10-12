from pydantic import BaseModel, ConfigDict


class CategoriaCrear(BaseModel):
    nombre: str


class CategoriaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str