from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.auth import login_requerido, usuario_actual
from app.errores import ErrorValidacion
from app.estados import ACTUALIZADO, ANALISIS
from app.extensions import db
from app.models import Bitacora, CorreccionTicket, Ticket
from app.rutas.basculista import formato_peso
from app.rutas.tickets import ERROR_FECHA, NUMERO_MAX, _fecha, _ticket_visible
from app.servicios import bitacora as svc_bitacora
from app.servicios import correcciones as svc_correcciones
from app.servicios import tickets as svc_tickets

bp = Blueprint("supervisor", __name__, url_prefix="/supervisor")

ETIQUETAS = {"peso": "Peso", "resultadoLey": "Resultado de ley", "observaciones": "Observaciones"}
ESTADOS_EDITABLES = (ANALISIS, ACTUALIZADO)


def _actuales(ticket: Ticket) -> dict:
    return {c: (formato_peso(v) if c == "peso" else str(v))
            for c in ETIQUETAS for v in [svc_correcciones.CAMPOS[c][0](ticket)]}


def _render_correccion(ticket, campo="peso", nuevo="", motivo=""):
    if campo not in ETIQUETAS:
        campo = "peso"
    actuales = _actuales(ticket) if ticket.estadoTicket in ESTADOS_EDITABLES else {}
    return render_template("correccion.html", ticket=ticket, etiquetas=ETIQUETAS,
                           campo=campo, nuevo=nuevo, motivo=motivo, actuales=actuales,
                           editable=ticket.estadoTicket in ESTADOS_EDITABLES)


@bp.route("/correccion/<int:numero>", methods=["GET", "POST"])
@login_requerido("supervisor")
def corregir(numero: int):
    ticket = _ticket_visible(numero)
    if request.method == "GET":
        return _render_correccion(ticket, request.args.get("campo", "peso"))
    campo = request.form.get("campo", "")
    nuevo = request.form.get("valorNuevo", "")
    motivo = request.form.get("motivo", "")
    try:
        c = svc_correcciones.solicitar(usuario_actual(), ticket.numeroTicket, campo, nuevo, motivo)
    except ErrorValidacion as e:
        db.session.rollback()
        flash(str(e), "error")
        return _render_correccion(ticket, campo, nuevo, motivo)
    flash(f"Solicitud de corrección enviada - N.º {c.numeroCorreccion}", "ok")
    return redirect(url_for("tickets.detalle", numero=ticket.numeroTicket))


@bp.route("/aprobaciones", methods=["GET", "POST"])
@login_requerido("supervisor")
def aprobaciones():
    if request.method == "POST":
        accion = request.form.get("accion", "")
        texto = request.form.get("numeroCorreccion", "").strip()
        if accion not in ("aprobar", "rechazar"):
            flash("Acción no válida", "error")
        elif not (texto.isascii() and texto.isdigit()) or len(texto) > 10 \
                or not 1 <= int(texto) <= NUMERO_MAX:
            flash("Corrección no encontrada", "error")
        else:
            try:
                if accion == "aprobar":
                    svc_correcciones.aprobar(usuario_actual(), int(texto))
                    flash("Corrección aprobada", "ok")
                else:
                    svc_correcciones.rechazar(usuario_actual(), int(texto))
                    flash("Corrección rechazada", "ok")
            except ErrorValidacion as e:
                db.session.rollback()
                flash(str(e), "error")
        return redirect(url_for("supervisor.aprobaciones"))
    resueltas = (CorreccionTicket.query.filter(CorreccionTicket.estadoCorreccion != "pendiente")
                 .order_by(CorreccionTicket.numeroCorreccion.desc()).limit(10).all())
    return render_template("aprobaciones.html", pendientes=svc_correcciones.pendientes(),
                           resueltas=resueltas, etiquetas=ETIQUETAS)


@bp.route("/cerrar/<int:numero>", methods=["POST"])
@login_requerido("supervisor")
def cerrar(numero: int):
    ticket = _ticket_visible(numero)
    if ticket.estadoTicket not in ESTADOS_EDITABLES:
        raise ErrorValidacion("El ticket no puede cerrarse en su estado actual")
    svc_tickets.cerrar_ticket(usuario_actual(), ticket.numeroTicket)
    flash(f"Ticket {ticket.folio} cerrado", "ok")
    return redirect(url_for("tickets.detalle", numero=ticket.numeroTicket))


@bp.route("/bitacora")
@login_requerido("supervisor")
def bitacora():
    f = {k: request.args.get(k, "").strip() for k in ("desde", "hasta", "usuario", "accion")}
    error = None
    registros = []
    try:
        desde, hasta = _fecha(f["desde"]), _fecha(f["hasta"])
    except ValueError:
        error = ERROR_FECHA
    if error is None:
        try:
            registros = svc_bitacora.consultar(desde, hasta, f["usuario"] or None,
                                               f["accion"] or None)
        except ErrorValidacion as e:
            error = str(e)
    ids = {r.numeroTicket for r in registros if r.numeroTicket}
    folios = {t.numeroTicket: t.folio for t in Ticket.query.filter(Ticket.numeroTicket.in_(ids))} if ids else {}
    acciones = [a for (a,) in db.session.query(Bitacora.accion).distinct().order_by(Bitacora.accion)]
    return render_template("bitacora.html", registros=registros, filtros=f, error=error,
                           folios=folios, acciones=acciones)
