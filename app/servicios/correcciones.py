from datetime import date
from decimal import Decimal

from app.errores import ErrorValidacion
from app.estados import ACTUALIZADO, ANALISIS, APROBADA, EN_CORRECCION
from app.extensions import db
from app.models import CorreccionTicket, Ticket, Usuario
from app.servicios import bitacora, tickets
from app.servicios.analisis import validar_ley, validar_observaciones
from app.servicios.validacion import parse_decimal


def _validar_peso(valor) -> Decimal:
    return parse_decimal(str(valor), "peso", Decimal("0"), Decimal("80000"), 2, minimo_exclusivo=True)


def _set_peso(t: Ticket, v) -> None:
    t.pesaje.peso = v


def _set_ley(t: Ticket, v) -> None:
    t.analisis.resultadoLey = v


def _set_obs(t: Ticket, v) -> None:
    t.analisis.observaciones = v


# campo -> (leer, validar, aplicar)
CAMPOS = {
    "peso": (lambda t: t.pesaje.peso, _validar_peso, _set_peso),
    "resultadoLey": (lambda t: t.analisis.resultadoLey, validar_ley, _set_ley),
    "observaciones": (lambda t: t.analisis.observaciones or "", validar_observaciones, _set_obs),
}


def _obtener(numeroCorreccion: int) -> CorreccionTicket:
    c = db.session.get(CorreccionTicket, numeroCorreccion)
    if c is None:
        raise ErrorValidacion("Corrección no encontrada")
    if c.estadoCorreccion != "pendiente":
        raise ErrorValidacion("La corrección ya fue resuelta")
    return c


def solicitar(usuario: Usuario, numeroTicket: int, campo: str, valorNuevo: str,
              motivo: str) -> CorreccionTicket:
    ticket = tickets.obtener(numeroTicket)
    if campo not in CAMPOS:
        raise ErrorValidacion("Campo de corrección desconocido")
    if ticket.estadoTicket not in (ANALISIS, ACTUALIZADO):
        raise ErrorValidacion("El ticket no admite correcciones en su estado actual")
    if any(c.estadoCorreccion == "pendiente" for c in ticket.correcciones):
        raise ErrorValidacion("El ticket ya tiene una corrección pendiente")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ErrorValidacion("El motivo es obligatorio")
    if len(motivo) > 255:
        raise ErrorValidacion("El motivo no puede exceder 255 caracteres")
    leer, validar, _ = CAMPOS[campo]
    nuevo = validar(valorNuevo)
    c = CorreccionTicket(numeroTicket=ticket.numeroTicket, campo=campo,
                         valorAnterior=str(leer(ticket)), valorNuevo=str(nuevo), motivo=motivo,
                         estadoCorreccion="pendiente", fechaSolicitud=date.today(),
                         idSolicitante=usuario.id)
    db.session.add(c)
    db.session.flush()
    ticket.estadoPrevio = ticket.estadoTicket
    tickets.transicionar(ticket, EN_CORRECCION, usuario)
    bitacora.registrar(usuario, "Solicitar corrección",
                       f"{campo}: {c.valorAnterior} → {c.valorNuevo}. Motivo: {motivo}",
                       ticket.numeroTicket, c.numeroCorreccion)
    db.session.commit()
    return c


def aprobar(usuario: Usuario, numeroCorreccion: int) -> CorreccionTicket:
    c = _obtener(numeroCorreccion)
    ticket = c.ticket
    _, validar, aplicar = CAMPOS[c.campo]
    aplicar(ticket, validar(c.valorNuevo))
    c.estadoCorreccion = "aprobada"
    c.fechaResolucion = date.today()
    c.idRevisor = usuario.id
    tickets.transicionar(ticket, APROBADA, usuario)
    bitacora.registrar(usuario, "Aprobar corrección",
                       f"{c.campo}: {c.valorAnterior} → {c.valorNuevo}",
                       ticket.numeroTicket, c.numeroCorreccion)
    tickets.transicionar(ticket, ACTUALIZADO, usuario)
    db.session.commit()
    return c


def rechazar(usuario: Usuario, numeroCorreccion: int) -> CorreccionTicket:
    c = _obtener(numeroCorreccion)
    ticket = c.ticket
    previo = ticket.estadoPrevio  # antes de transicionar, que lo sobrescribe
    c.estadoCorreccion = "rechazada"
    c.fechaResolucion = date.today()
    c.idRevisor = usuario.id
    tickets.transicionar(ticket, previo, usuario)
    bitacora.registrar(usuario, "Rechazar corrección",
                       f"{c.campo}: se mantiene {c.valorAnterior}; solicitado {c.valorNuevo}",
                       ticket.numeroTicket, c.numeroCorreccion)
    db.session.commit()
    return c


def pendientes() -> list[CorreccionTicket]:
    return (CorreccionTicket.query.filter_by(estadoCorreccion="pendiente")
            .order_by(CorreccionTicket.numeroCorreccion).all())
