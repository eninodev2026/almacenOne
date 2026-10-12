#app\schemas\salida.py  
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SalidaDetalleCrear(BaseModel):
    presentacion_id: int
    cantidad: Decimal = Field(gt=0)


class SalidaCrear(BaseModel):
    bodega_id: int
    detalles: list[SalidaDetalleCrear] = Field(min_length=1)


class SalidaRespuesta(BaseModel):
    movimiento_id: int
    bodega_id: int
    productos_afectados: int


class SalidaListado(BaseModel):
    id: int
    fecha: datetime
    bodega_nombre: str
    productos: int
    estado: str
    motivo_anulacion: str | None
    fecha_anulacion: datetime | None