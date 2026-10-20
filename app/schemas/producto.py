#app\schemas\producto.py
from pydantic import BaseModel, ConfigDict


class ProductoCrear(BaseModel):
    codigo: str
    nombre: str
    categoria_id: int
    unidad_base_id: int

class ProductoEditar(BaseModel):
    codigo: str
    nombre: str
    categoria_id: int
    unidad_base_id: int
    
    
class ProductoLista(BaseModel):
    id: int
    codigo: str
    nombre: str
    categoria_id: int
    unidad_base_id: int
    categoria_nombre: str
    unidad_base_nombre: str    
    
class ProductoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    categoria_id: int
    unidad_base_id: int