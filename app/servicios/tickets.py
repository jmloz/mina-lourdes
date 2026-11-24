from datetime import date

from sqlalchemy.exc import IntegrityError

from app.errores import ErrorValidacion
from app.estados import CERRADO, EMITIDO, PENDIENTE, puede_transicionar
from app.extensions import db
from app.models import Pesaje, Ticket, Usuario
from app.servicios import bitacora

_YA_TIENE = "El pesaje ya tiene un ticket"


def transicionar(ticket: Ticket, nuevo: str, usuario: Usuario) -> None:
    actual = ticket.estadoTicket
    if not puede_transicionar(actual, nuevo):
        raise ErrorValidacion(f"Transición no permitida: {actual} → {nuevo}")
    ticket.estadoPrevio = actual
    ticket.estadoTicket = nuevo
    bitacora.registrar(usuario, "Cambio de estado", f"{actual} → {nuevo}", ticket.numeroTicket)


def emitir_ticket(usuario: Usuario, idPesaje: int) -> Ticket:
    pesaje = db.session.get(Pesaje, idPesaje)
    if pesaje is None or pesaje.ticket is not None:
        raise ErrorValidacion(_YA_TIENE)
    try:
        ticket = Ticket(fechaEmision=date.today(), estadoTicket=EMITIDO,
                        numeroPesaje=pesaje.idPesaje, idUsuario=usuario.id)
        db.session.add(ticket)
        db.session.flush()
        bitacora.registrar(usuario, "Emitir ticket",
                           f"Ticket {ticket.folio} emitido para pesaje {pesaje.idPesaje}",
                           ticket.numeroTicket)
        transicionar(ticket, PENDIENTE, usuario)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ErrorValidacion(_YA_TIENE)
    return ticket


def obtener(numeroTicket: int) -> Ticket:
    ticket = db.session.get(Ticket, numeroTicket)
    if ticket is None:
        raise ErrorValidacion("Ticket no encontrado")
    return ticket


def buscar(desde: date | None = None, hasta: date | None = None, estado: str | None = None,
           numero: int | None = None, idUsuario: int | None = None) -> list[Ticket]:
    if desde and hasta and desde > hasta:
        raise ErrorValidacion("El rango de fechas no es válido")
    q = Ticket.query
    if desde:
        q = q.filter(Ticket.fechaEmision >= desde)
    if hasta:
        q = q.filter(Ticket.fechaEmision <= hasta)
    if estado:
        q = q.filter(Ticket.estadoTicket == estado)
    if numero is not None:
        q = q.filter(Ticket.numeroTicket == numero)
    if idUsuario is not None:
        q = q.filter(Ticket.idUsuario == idUsuario)
    return q.order_by(Ticket.numeroTicket.desc()).all()


def ultimos(limite: int = 20) -> list[Ticket]:
    return Ticket.query.order_by(Ticket.numeroTicket.desc()).limit(limite).all()


def cerrar_ticket(usuario: Usuario, numeroTicket: int) -> Ticket:
    ticket = obtener(numeroTicket)
    transicionar(ticket, CERRADO, usuario)
    bitacora.registrar(usuario, "Cerrar ticket", f"Ticket {ticket.folio} cerrado", ticket.numeroTicket)
    db.session.commit()
    return ticket
