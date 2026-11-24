from datetime import date, datetime, time

from app.errores import ErrorValidacion
from app.extensions import db
from app.models import Bitacora, Usuario


def registrar(usuario: Usuario | None, accion: str, detalle: str,
              numeroTicket: int | None = None, numeroCorreccion: int | None = None) -> Bitacora:
    reg = Bitacora(
        usuarioResponsable=usuario.usuario if usuario else "sistema",
        fechaHoraB=datetime.now(),
        accion=accion,
        detalleCambio=detalle,
        numeroTicket=numeroTicket,
        numeroCorreccion=numeroCorreccion,
    )
    db.session.add(reg)
    return reg


def consultar(desde: date | None, hasta: date | None, usuario: str | None,
              accion: str | None) -> list[Bitacora]:
    if desde and hasta and desde > hasta:
        raise ErrorValidacion("El rango de fechas no es válido")
    q = Bitacora.query
    if desde:
        q = q.filter(Bitacora.fechaHoraB >= datetime.combine(desde, time.min))
    if hasta:
        q = q.filter(Bitacora.fechaHoraB <= datetime.combine(hasta, time.max))
    if usuario:
        q = q.filter(Bitacora.usuarioResponsable == usuario)
    if accion:
        q = q.filter(Bitacora.accion == accion)
    return q.order_by(Bitacora.fechaHoraB.desc(), Bitacora.idBitacora.desc()).all()
