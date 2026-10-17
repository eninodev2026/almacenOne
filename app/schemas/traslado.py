#app\schemas\traslado.py
from decimal import Decimal

from pydantic import BaseModel, Field


class TrasladoLinea(BaseModel):
    presentacion_id: int
    cantidad: Decimal = Field(gt=0)


class TrasladoCrear(BaseModel):
    bodega_origen_id: int
    bodega_destino_id: int
    observacion: str | None = None
    detalles: list[TrasladoLinea] = Field(min_length=1)


class TrasladoRespuesta(BaseModel):
    movimiento_id: int
    bodega_origen_id: int
    bodega_destino_id: int
    productos_afectados: int
    estado: str


class ResolucionTraslado(BaseModel):
    observacion: str | None = None