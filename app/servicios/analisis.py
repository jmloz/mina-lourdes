from datetime import date
from decimal import Decimal

from app.errores import ErrorValidacion
from app.estados import ANALISIS, PENDIENTE
from app.extensions import db
from app.models import Analisis, Usuario
from app.servicios import bitacora, tickets
from app.servicios.validacion import parse_decimal


def validar_ley(valor) -> Decimal:
    return parse_decimal(str(valor), "resultado de ley", Decimal("0"), Decimal("100"), 3)


def validar_observaciones(texto) -> str:
    texto = (texto or "").strip()
    if len(texto) > 255:
        raise ErrorValidacion("Las observaciones no pueden exceder 255 caracteres")
    return texto


def registrar_analisis(usuario: Usuario, numeroTicket: int, resultadoLey: Decimal | str,
                       observaciones: str = "") -> Analisis:
    ticket = tickets.obtener(numeroTicket)
    if ticket.estadoTicket != PENDIENTE:
        raise ErrorValidacion("El ticket no está pendiente de análisis")
    ley = validar_ley(resultadoLey)
    obs = validar_observaciones(observaciones)
    a = Analisis(fechaAnalisis=date.today(), resultadoLey=ley, observaciones=obs,
                 numeroTicket=ticket.numeroTicket, idUsuario=usuario.id)
    db.session.add(a)
    bitacora.registrar(usuario, "Registrar análisis",
                       f"Ley {ley} registrada para ticket {ticket.folio}", ticket.numeroTicket)
    tickets.transicionar(ticket, ANALISIS, usuario)
    db.session.commit()
    return a
