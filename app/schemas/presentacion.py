#app\schemas\presentacion.py
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PresentacionCrear(BaseModel):
    producto_id: int
    unidad_id: int
    factor: Decimal = Field(gt=0)
    precio_venta: Decimal = Field(ge=0)


class PresentacionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    unidad_id: int
    factor: Decimal
    precio_venta: Decimal
    producto_nombre: str
    unidad_nombre: str
    codigo_barras: str | None = None