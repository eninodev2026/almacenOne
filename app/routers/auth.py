# app/routers/auth.py
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import codigos_permisos, get_current_user, ip_cliente, registrar_evento
from app.models.usuario import Sesion, Usuario
from app.schemas.usuario import LoginPeticion, UsuarioSesion
from app.security import (
    COOKIE_ACCESS,
    crear_access_token,
    decodificar_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 15
# Hash falso para que el tiempo de respuesta sea igual si el usuario no existe
_HASH_FALSO = hash_password("no-existe-este-usuario")


def armar_sesion(usuario: Usuario) -> UsuarioSesion:
    return UsuarioSesion(
        id=usuario.id,
        username=usuario.username,
        nombre=usuario.nombre,
        rol=usuario.rol.nombre,
        permisos=sorted(codigos_permisos(usuario)),
    )


@router.post("/login", response_model=UsuarioSesion)
def login(datos: LoginPeticion, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = ip_cliente(request)
    username = datos.username.strip().lower()
    ahora = datetime.now(timezone.utc)

    usuario = db.scalars(select(Usuario).where(Usuario.username == username)).first()

    if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
        registrar_evento(db, "LOGIN_BLOQUEADO", usuario.id, username, "Cuenta bloqueada", ip)
        db.commit()
        raise HTTPException(status_code=429, detail="Cuenta bloqueada temporalmente. Intenta más tarde.")

    password_ok = verify_password(datos.password, usuario.password_hash if usuario else _HASH_FALSO)

    if usuario is None or not password_ok or not usuario.activo:
        if usuario is not None and not password_ok:
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= MAX_INTENTOS:
                usuario.bloqueado_hasta = ahora + timedelta(minutes=BLOQUEO_MINUTOS)
                usuario.intentos_fallidos = 0
        registrar_evento(db, "LOGIN_FALLIDO", usuario.id if usuario else None, username, "Credenciales inválidas", ip)
        db.commit()
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None

    sesion = Sesion(
        usuario_id=usuario.id,
        inicio=ahora,
        ultimo_uso=ahora,
        expira_en=ahora + timedelta(minutes=settings.access_minutes),
        ip=ip,
    )
    db.add(sesion)
    db.flush()  # asigna sesion.id

    registrar_evento(db, "LOGIN_OK", usuario.id, username, f"sesión {sesion.id}", ip)
    token = crear_access_token(usuario.id, sesion.id)
    respuesta = armar_sesion(usuario)
    db.commit()

    response.set_cookie(
        key=COOKIE_ACCESS,
        value=token,
        max_age=settings.access_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return respuesta


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_ACCESS)
    payload = decodificar_token(token) if token else None

    if payload and payload.get("sid") is not None:
        sesion = db.get(Sesion, int(payload["sid"]))
        if sesion is not None and sesion.cierre is None:
            sesion.cierre = datetime.now(timezone.utc)
            sesion.motivo_cierre = "LOGOUT"
            registrar_evento(db, "LOGOUT", sesion.usuario_id, None, f"sesión {sesion.id}", ip_cliente(request))
            db.commit()

    response.delete_cookie(COOKIE_ACCESS, path="/")


@router.get("/me", response_model=UsuarioSesion)
def me(usuario: Usuario = Depends(get_current_user)):
    return armar_sesion(usuario)