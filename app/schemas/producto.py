from pydantic import BaseModel, ConfigDict


class ProductoCrear(BaseModel):
    codigo: str
    nombre: str
    categoria_id: int
    unidad_base_id: int


class ProductoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    categoria_id: int
    unidad_base_id: int