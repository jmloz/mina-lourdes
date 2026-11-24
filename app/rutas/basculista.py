from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.auth import login_requerido, usuario_actual
from app.errores import ErrorBascula, ErrorValidacion
from app.extensions import db
from app.models import Pesaje
from app.rutas.tickets import NUMERO_MAX
from app.servicios import bascula as svc_bascula
from app.servicios import pesajes as svc_pesajes
from app.servicios import tickets as svc_tickets

bp = Blueprint("basculista", __name__, url_prefix="/basculista")


@bp.app_template_filter("peso")
def formato_peso(valor) -> str:
    try:
        return f"{Decimal(valor):,.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return "" if valor is None else str(valor)


def _render_captura(peso_manual=""):
    ahora = datetime.now()
    return render_template("captura_pesaje.html", peso=session.get("lectura"),
                           fecha=ahora.date(), hora=ahora.time().replace(microsecond=0),
                           bascula=svc_bascula.obtener(), peso_manual=peso_manual)


@bp.route("/captura", methods=["GET", "POST"])
@login_requerido("basculista")
def captura():
    if request.method == "GET":
        return _render_captura()
    accion = request.form.get("accion")
    try:
        if accion == "leer":
            session.pop("lectura", None)
            session["lectura"] = str(svc_bascula.leer_peso())
            return _render_captura()
        if accion == "guardar":
            lectura = session.get("lectura")
            if not lectura:
                raise ErrorValidacion("Primero lea el peso de la báscula")
            pesaje = svc_pesajes.registrar_pesaje(usuario_actual(), lectura)
            session.pop("lectura", None)
            flash(f"Pesaje registrado - N.º de pesaje: {pesaje.idPesaje} - "
                  f"Peso: {formato_peso(pesaje.peso)} kg - "
                  f"Fecha: {pesaje.fechaPesaje.strftime('%d/%m/%Y')} - "
                  f"Hora: {pesaje.horaPesaje.strftime('%H:%M:%S')}", "ok")
            return redirect(url_for("basculista.captura"))
        if accion == "guardar_manual":
            peso_manual = request.form.get("peso_manual", "")
            pesaje = svc_pesajes.registrar_pesaje_manual(usuario_actual(), peso_manual)
            flash(f"Pesaje registrado (captura manual) - N.º de pesaje: {pesaje.idPesaje} - "
                  f"Peso: {formato_peso(pesaje.peso)} kg - "
                  f"Fecha: {pesaje.fechaPesaje.strftime('%d/%m/%Y')} - "
                  f"Hora: {pesaje.horaPesaje.strftime('%H:%M:%S')}", "ok")
            return redirect(url_for("basculista.captura"))
    except ErrorValidacion as e:
        db.session.rollback()
        flash(str(e), "error")
        return _render_captura(request.form.get("peso_manual", ""))
    flash("Acción no reconocida", "error")
    return _render_captura()


@bp.route("/conexion", methods=["POST"])
@login_requerido("basculista")
def conexion():
    conectada = svc_bascula.obtener().estadoConexion == svc_bascula.CONECTADA
    svc_bascula.set_conexion(not conectada)
    session.pop("lectura", None)
    flash("Báscula desconectada" if conectada else "Báscula conectada", "ok")
    return redirect(url_for("basculista.captura"))


@bp.route("/generar", methods=["GET", "POST"])
@login_requerido("basculista")
def generar():
    usuario = usuario_actual()
    if request.method == "POST":
        texto = request.form.get("idPesaje", "").strip()
        if not (texto.isascii() and texto.isdigit() and len(texto) <= 10
                and 1 <= int(texto) <= NUMERO_MAX):
            flash("Seleccione un pesaje válido", "error")
            return redirect(url_for("basculista.generar"))
        id_pesaje = int(texto)
        pesaje = db.session.get(Pesaje, id_pesaje)
        if pesaje is not None and pesaje.idUsuario != usuario.id:
            abort(403)
        try:
            ticket = svc_tickets.emitir_ticket(usuario, id_pesaje)
        except ErrorValidacion as e:
            flash(str(e), "error")
            return redirect(url_for("basculista.generar"))
        flash(f"Ticket {ticket.folio} generado", "ok")
        return redirect(url_for("tickets.imprimir", numero=ticket.numeroTicket))
    return render_template("generar_ticket.html", pesajes=svc_pesajes.sin_ticket(usuario))
