# app/main.py
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from app.config import settings
from app.deps import get_current_user
from app.routers import auth
from app.routers import usuario
from app.routers import categoria
from app.routers import unidad_medida
from app.routers import producto
from app.routers import presentacion
from app.routers import proveedor
from app.routers import bodega
from app.routers import tipo_movimiento
from app.routers import compra
from app.routers import stock
from app.routers import salida
from app.routers import inventario
from app.routers import reporte
from app.routers import traslado
app = FastAPI(title="Inventario")

# 1. MIDDLEWARE DE CORS (orígenes explícitos: obligatorio para usar cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.lista_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Encabezado que exige get_current_user en las peticiones de escritura.
# Solo sirve para que Swagger muestre el botón Authorize y lo envíe; la validación sigue en deps.py
encabezado_swagger = APIKeyHeader(name="x-requested-with", auto_error=False)

# 2. REGISTRAR ROUTERS
# /auth queda abierto (login). Todo lo demás exige sesión válida.
app.include_router(auth.router)

protegido = [Depends(get_current_user), Depends(encabezado_swagger)]
app.include_router(usuario.router, dependencies=protegido)
app.include_router(categoria.router, dependencies=protegido)
app.include_router(unidad_medida.router, dependencies=protegido)
app.include_router(producto.router, dependencies=protegido)
app.include_router(presentacion.router, dependencies=protegido)
app.include_router(proveedor.router, dependencies=protegido)
app.include_router(bodega.router, dependencies=protegido)
app.include_router(tipo_movimiento.router, dependencies=protegido)
app.include_router(compra.router, dependencies=protegido)
app.include_router(stock.router, dependencies=protegido)
app.include_router(salida.router, dependencies=protegido)
app.include_router(inventario.router, dependencies=protegido)
app.include_router(reporte.router, dependencies=protegido)
app.include_router(traslado.router, dependencies=protegido)

@app.get("/health")
def health():
    return {"status": "ok"}