from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnulacionPeticion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    motivo: str = Field(min_length=5, max_length=500)


class AnulacionRespuesta(BaseModel):
    id: int
    estado: str
    motivo_anulacion: str
    fecha_anulacion: datetime