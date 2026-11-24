from functools import wraps

from flask import abort, redirect, session, url_for

from app.extensions import db
from app.models import Usuario


def usuario_actual() -> Usuario | None:
    if "idUsuario" not in session:
        return None
    return db.session.get(Usuario, session["idUsuario"])


def login_requerido(*roles: str):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            usuario = usuario_actual()
            if usuario is None:
                session.pop("idUsuario", None)
                return redirect(url_for("principal.login"))
            if roles and usuario.rol not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador
