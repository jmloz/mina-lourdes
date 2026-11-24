from datetime import date, datetime

from flask import Blueprint, abort, render_template, request

from app.auth import login_requerido, usuario_actual
from app.errores import ErrorValidacion
from app.estados import (ANALISIS, ACTUALIZADO, CERRADO, EN_CORRECCION,
                         PENDIENTE)
from app.extensions import db
from app.models import Ticket
from app.servicios import tickets as svc_tickets

bp = Blueprint("tickets", __name__, url_prefix="/tickets")

ESTADOS = [PENDIENTE, ANALISIS, EN_CORRECCION, ACTUALIZADO, CERRADO]
ERROR_FECHA = "Formato de fecha inválido (AAAA-MM-DD)"


def _fecha(texto: str) -> date | None:
    texto = texto.strip()
    return datetime.strptime(texto, "%Y-%m-%d").date() if texto else None


NUMERO_MAX = 2**31 - 1


def _ticket_visible(numero: int) -> Ticket:
    ticket = db.session.get(Ticket, numero) if 1 <= numero <= NUMERO_MAX else None
    if ticket is None:
        abort(404, description="Ticket no encontrado")
    u = usuario_actual()
    if u.rol == "basculista" and ticket.idUsuario != u.id:
        abort(403)
    return ticket


@bp.route("/")
@login_requerido("basculista", "laboratorista", "supervisor")
def consulta():
    u = usuario_actual()
    f = {k: request.args.get(k, "").strip() for k in ("desde", "hasta", "estado", "numero")}
    error = None
    tickets = []
    try:
        desde, hasta = _fecha(f["desde"]), _fecha(f["hasta"])
    except ValueError:
        error = ERROR_FECHA
    numero = None
    if error is None and f["numero"]:
        if not (f["numero"].isascii() and f["numero"].isdigit()):
            error = "El número de ticket debe ser numérico"
        elif len(f["numero"]) > 10 or not 1 <= int(f["numero"]) <= NUMERO_MAX:
            error = "Ticket no encontrado"
        else:
            numero = int(f["numero"])
    if error is None:
        try:
            tickets = svc_tickets.buscar(desde, hasta, f["estado"] or None,
                                         numero,
                                         u.id if u.rol == "basculista" else None)
        except ErrorValidacion as e:
            error = str(e)
    return render_template("consulta_tickets.html", tickets=tickets, filtros=f,
                           estados=ESTADOS, error=error)


@bp.route("/<int:numero>")
@login_requerido("basculista", "laboratorista", "supervisor")
def detalle(numero: int):
    return render_template("detalle_ticket.html", ticket=_ticket_visible(numero))


@bp.route("/<int:numero>/imprimir")
@login_requerido("basculista", "laboratorista", "supervisor")
def imprimir(numero: int):
    return render_template("ticket_impresion.html", ticket=_ticket_visible(numero))
