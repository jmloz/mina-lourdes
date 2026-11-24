from flask import (Blueprint, current_app, flash, redirect, render_template, request,
                   session, url_for)

from app.auth import login_requerido, usuario_actual
from app.extensions import db
from app.models import Usuario
from app.servicios import bitacora as svc_bitacora

bp = Blueprint("principal", __name__)

# (etiqueta, endpoint, roles, descripción)
MENU = [
    ("Captura de pesaje", "basculista.captura", ("basculista",),
     "Leer el peso de la báscula y registrarlo."),
    ("Generación de ticket", "basculista.generar", ("basculista",),
     "Emitir el ticket de un pesaje registrado."),
    ("Registro de análisis", "laboratorio.historial", ("laboratorista",),
     "Registrar la ley de los tickets pendientes."),
    ("Historial de últimos tickets", "laboratorio.historial", ("laboratorista",),
     "Revisar los últimos tickets emitidos."),
    ("Consulta de tickets", "tickets.consulta", ("basculista", "laboratorista", "supervisor"),
     "Buscar tickets por fecha, estado o número."),
    ("Correcciones y aprobaciones", "supervisor.aprobaciones", ("supervisor",),
     "Aprobar o rechazar correcciones solicitadas."),
    ("Bitácora", "supervisor.bitacora", ("supervisor",),
     "Auditar las acciones realizadas en el sistema."),
]


def opciones_menu(rol: str) -> list[dict]:
    items = []
    for etiqueta, endpoint, roles, descripcion in MENU:
        if rol in roles:
            url = url_for(endpoint) if endpoint in current_app.view_functions else None
            items.append({"etiqueta": etiqueta, "url": url, "descripcion": descripcion})
    return items


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip()
        u = Usuario.query.filter_by(usuario=nombre).first()
        if u is not None and u.check_password(request.form.get("password", "")):
            session.clear()
            session["idUsuario"] = u.id
            svc_bitacora.registrar(u, "Iniciar sesión", f"Inicio de sesión de {u.usuario}")
            db.session.commit()
            return redirect(url_for("principal.menu"))
        flash("Usuario o contraseña incorrectos", "error")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    u = usuario_actual()
    if u is not None:
        svc_bitacora.registrar(u, "Cerrar sesión", f"Cierre de sesión de {u.usuario}")
        db.session.commit()
    session.clear()
    return redirect(url_for("principal.login"))


@bp.route("/")
@login_requerido()
def menu():
    u = usuario_actual()
    return render_template("menu.html", opciones=opciones_menu(u.rol))
