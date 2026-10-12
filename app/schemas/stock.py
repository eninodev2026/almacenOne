#app\schemas\stock.py
from decimal import Decimal

from pydantic import BaseModel


class PresentacionStock(BaseModel):
    presentacion_id: int
    unidad_nombre: str
    factor: Decimal
    precio_venta: Decimal


class SaldoBodega(BaseModel):
    bodega_id: int
    bodega_nombre: str
    cantidad_disponible: Decimal


class StockProducto(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    categoria_nombre: str
    unidad_base_nombre: str
    presentaciones: list[PresentacionStock]
    saldos: list[SaldoBodega]
    cantidad_total: Decimal