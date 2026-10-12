from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import registrar_evento, require_permission
from app.models.usuario import Rol, Sesion, Usuario
from app.schemas.usuario import RolListado, SesionActiva, UsuarioCrear, UsuarioEditar, UsuarioListado
from app.security import hash_password

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(require_permission("usuario.gestionar"))],
)


def _listado(u: Usuario) -> UsuarioListado:
    return UsuarioListado(id=u.id, username=u.username, nombre=u.nombre, rol=u.rol.nombre, activo=u.activo)


@router.get("/", response_model=list[UsuarioListado])
def listar(db: Session = Depends(get_db)):
    return [_listado(u) for u in db.scalars(select(Usuario).order_by(Usuario.username)).all()]


@router.get("/roles", response_model=list[RolListado])
def listar_roles(db: Session = Depends(get_db)):
    return db.scalars(select(Rol).order_by(Rol.nombre)).all()


@router.get("/sesiones", response_model=list[SesionActiva])
def sesiones_activas(db: Session = Depends(get_db)):
    ahora = datetime.now(timezone.utc)
    sesiones = db.scalars(
        select(Sesion)
        .where(Sesion.cierre.is_(None), Sesion.expira_en > ahora)
        .order_by(Sesion.inicio.desc())
    ).all()
    return [
        SesionActiva(
            id=s.id,
            usuario_id=s.usuario_id,
            username=s.usuario.username,
            nombre=s.usuario.nombre,
            rol=s.usuario.rol.nombre,
            inicio=s.inicio,
            ultimo_uso=s.ultimo_uso,
            ip=s.ip,
        )
        for s in sesiones
    ]


@router.post("/sesiones/{sesion_id}/cerrar")
def cerrar_sesion_remota(sesion_id: int, db: Session = Depends(get_db),
                         admin: Usuario = Depends(require_permission("usuario.gestionar"))):
    sesion = db.get(Sesion, sesion_id)
    if sesion is None:
        raise HTTPException(status_code=404, detail="La sesión no existe")
    if sesion.cierre is not None:
        raise HTTPException(status_code=409, detail="La sesión ya está cerrada")

    sesion.cierre = datetime.now(timezone.utc)
    sesion.motivo_cierre = "CERRADA_POR_ADMIN"
    registrar_evento(
        db, "SESION_CERRADA_ADMIN", admin.id, admin.username,
        f"cerró la sesión {sesion.id} de {sesion.usuario.username}", None,
    )
    db.commit()
    return {"ok": True}


@router.post("/", response_model=UsuarioListado, status_code=201)
def crear(datos: UsuarioCrear, db: Session = Depends(get_db),
          admin: Usuario = Depends(require_permission("usuario.gestionar"))):
    if db.get(Rol, datos.rol_id) is None:
        raise HTTPException(status_code=404, detail="El rol no existe")
    if db.scalars(select(Usuario).where(Usuario.username == datos.username)).first():
        raise HTTPException(status_code=409, detail="Ese nombre de usuario ya existe")

    usuario = Usuario(
        username=datos.username, nombre=datos.nombre,
        password_hash=hash_password(datos.password), rol_id=datos.rol_id,
    )
    db.add(usuario)
    db.flush()
    registrar_evento(db, "USUARIO_CREADO", admin.id, admin.username, f"creó a {usuario.username}", None)
    db.commit()
    db.refresh(usuario)
    return _listado(usuario)


@router.patch("/{usuario_id}", response_model=UsuarioListado)
def editar(usuario_id: int, datos: UsuarioEditar, db: Session = Depends(get_db),
           admin: Usuario = Depends(require_permission("usuario.gestionar"))):
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    if usuario.id == admin.id and (datos.activo is False or
                                   (datos.rol_id is not None and datos.rol_id != usuario.rol_id)):
        raise HTTPException(status_code=409, detail="No puedes desactivarte ni cambiar tu propio rol")

    if datos.rol_id is not None:
        if db.get(Rol, datos.rol_id) is None:
            raise HTTPException(status_code=404, detail="El rol no existe")
        usuario.rol_id = datos.rol_id
    if datos.nombre is not None:
        usuario.nombre = datos.nombre
    if datos.activo is not None:
        usuario.activo = datos.activo
    if datos.password is not None:
        usuario.password_hash = hash_password(datos.password)

    registrar_evento(db, "USUARIO_EDITADO", admin.id, admin.username, f"editó a {usuario.username}", None)
    db.commit()
    db.refresh(usuario)
    return _listado(usuario)