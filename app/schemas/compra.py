# app/schemas/compra.py
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompraDetalleCrear(BaseModel):
    presentacion_id: int
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)
    descuento: Decimal = Field(default=0, ge=0)


class CompraCrear(BaseModel):
    proveedor_id: int
    numero_factura: str
    fecha_emision: date
    fecha_compra: date
    condicion_pago: str
    bodega_id: int
    observacion: str | None = None
    detalles: list[CompraDetalleCrear] = Field(min_length=1)


class CompraDetalleRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    presentacion_id: int
    cantidad: Decimal
    cantidad_base: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    total_linea: Decimal
    costo_unitario_base: Decimal


class CompraRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proveedor_id: int
    numero_factura: str
    fecha_emision: date
    fecha_compra: date
    condicion_pago: str
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    observacion: str | None
    estado: str
    motivo_anulacion: str | None
    fecha_anulacion: datetime | None
    detalles: list[CompraDetalleRespuesta]


# ==============================================================================
# NUEVOS ESQUEMAS PARA IMPORTACIÓN DESDE DTE (FACTURA ELECTRÓNICA)
# ==============================================================================

class DTELineaImportar(BaseModel):
    descripcion: str
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)
    descuento: Decimal = Field(default=0, ge=0)


class DTEImportarSchema(BaseModel):
    """Esquema para recibir los datos extraídos del JSON del DTE"""
    nit_proveedor: str = Field(..., description="NIT del emisor del DTE")
    nombre_proveedor: str
    nrc_proveedor: str | None = None
    telefono_proveedor: str | None = None
    correo_proveedor: str | None = None
    direccion_proveedor: str | None = None
    
    numero_factura: str = Field(..., description="Generalmente el 'numeroControl' del DTE")
    fecha_emision: date
    bodega_id: int
    condicion_pago: str = "Contado"
    observacion: str | None = None
    
    detalles: list[DTELineaImportar] = Field(min_length=1)