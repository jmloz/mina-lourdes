from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import login_requerido, usuario_actual
from app.errores import ErrorValidacion
from app.estados import PENDIENTE
from app.extensions import db
from app.rutas.tickets import _ticket_visible
from app.servicios import analisis as svc_analisis
from app.servicios import tickets as svc_tickets

bp = Blueprint("laboratorio", __name__, url_prefix="/laboratorio")


@bp.route("/historial")
@login_requerido("laboratorista")
def historial():
    return render_template("historial.html", tickets=svc_tickets.ultimos(20),
                           pendiente=PENDIENTE)


def _render(ticket, ley="", observaciones=""):
    return render_template("registro_analisis.html", ticket=ticket, ley=ley,
                           observaciones=observaciones, pendiente=PENDIENTE)


@bp.route("/analisis/<int:numero>", methods=["GET", "POST"])
@login_requerido("laboratorista")
def analisis(numero: int):
    ticket = _ticket_visible(numero)
    if request.method == "GET":
        return _render(ticket)
    ley = request.form.get("resultadoLey", "")
    obs = request.form.get("observaciones", "")
    try:
        a = svc_analisis.registrar_analisis(usuario_actual(), ticket.numeroTicket, ley, obs)
    except ErrorValidacion as e:
        db.session.rollback()
        flash(str(e), "error")
        return _render(ticket, ley, obs)
    flash(f"Análisis registrado - N.º de análisis: {a.numeroAnalisis} - "
          f"Ley: {a.resultadoLey:.3f} %", "ok")
    return redirect(url_for("laboratorio.analisis", numero=ticket.numeroTicket))
