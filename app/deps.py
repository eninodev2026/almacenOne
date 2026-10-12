#app\deps.py
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import BitacoraSeguridad, Sesion, Usuario
from app.security import COOKIE_ACCESS, decodificar_token

_METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}
_SEGUNDOS_ENTRE_ACTUALIZACIONES = 60


def ip_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def registrar_evento(db: Session, evento: str, usuario_id: int | None,
                     username: str | None, detalle: str, ip: str | None) -> None:
    db.add(BitacoraSeguridad(
        evento=evento, usuario_id=usuario_id, username_intentado=username,
        detalle=detalle[:255], ip=ip,
    ))


def codigos_permisos(usuario: Usuario) -> set[str]:
    return {p.codigo for p in usuario.rol.permisos}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    token = request.cookies.get(COOKIE_ACCESS)
    payload = decodificar_token(token) if token else None
    if payload is None or payload.get("sid") is None:
        raise HTTPException(status_code=401, detail="Sesión no válida")

    ahora = datetime.now(timezone.utc)
    sesion = db.get(Sesion, int(payload["sid"]))
    if (sesion is None or sesion.cierre is not None
            or sesion.expira_en <= ahora
            or sesion.usuario_id != int(payload["sub"])):
        raise HTTPException(status_code=401, detail="Sesión no válida")

    # Marca de actividad (como máximo una vez por minuto, para no escribir en cada petición)
    if (ahora - sesion.ultimo_uso).total_seconds() > _SEGUNDOS_ENTRE_ACTUALIZACIONES:
        sesion.ultimo_uso = ahora
        db.commit()

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        sesion.cierre = ahora
        sesion.motivo_cierre = "USUARIO_INACTIVO"
        db.commit()
        raise HTTPException(status_code=401, detail="Sesión no válida")

    # Defensa CSRF extra: toda escritura debe traer este header (el front lo manda)
    if request.method not in _METODOS_SEGUROS and request.headers.get("x-requested-with") != "fetch":
        raise HTTPException(status_code=403, detail="Petición no permitida")

    return usuario


def require_permission(codigo: str):
    def _guardia(request: Request, usuario: Usuario = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> Usuario:
        if codigo not in codigos_permisos(usuario):
            registrar_evento(
                db, "ACCESO_DENEGADO", usuario.id, usuario.username,
                f"{request.method} {request.url.path} requiere {codigo}", ip_cliente(request),
            )
            db.commit()
            raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
        return usuario
    return _guardia