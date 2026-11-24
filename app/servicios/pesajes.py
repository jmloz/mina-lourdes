from datetime import datetime
from decimal import Decimal

from app.errores import ErrorBascula, ErrorValidacion
from app.extensions import db
from app.models import Pesaje, Ticket, Usuario
from app.servicios import bascula, bitacora
from app.servicios.validacion import parse_decimal


def registrar_pesaje(usuario: Usuario, peso: Decimal | str) -> Pesaje:
    valor = parse_decimal(str(peso), "peso", Decimal("0"), Decimal("80000"), 2,
                          minimo_exclusivo=True)
    b = bascula.obtener()
    if b.estadoConexion != bascula.CONECTADA:
        raise ErrorBascula("No hay comunicación con la báscula")
    ahora = datetime.now()
    pesaje = Pesaje(peso=valor, fechaPesaje=ahora.date(), horaPesaje=ahora.time().replace(microsecond=0),
                    lecturaValida=True, idBascula=b.idBascula, idUsuario=usuario.id)
    db.session.add(pesaje)
    bitacora.registrar(usuario, "Registrar pesaje", f"Peso registrado: {valor} kg")
    db.session.commit()
    return pesaje


def registrar_pesaje_manual(usuario: Usuario, peso: Decimal | str) -> Pesaje:
    b = bascula.obtener()
    if b.estadoConexion != bascula.DESCONECTADA:
        raise ErrorValidacion("La captura manual solo está disponible con la báscula desconectada")
    valor = parse_decimal(str(peso), "peso", Decimal("0"), Decimal("80000"), 2,
                          minimo_exclusivo=True)
    ahora = datetime.now()
    pesaje = Pesaje(peso=valor, fechaPesaje=ahora.date(), horaPesaje=ahora.time().replace(microsecond=0),
                    lecturaValida=False, idBascula=b.idBascula, idUsuario=usuario.id)
    db.session.add(pesaje)
    bitacora.registrar(usuario, "Captura manual", f"Peso capturado manualmente: {valor} kg")
    db.session.commit()
    return pesaje


def sin_ticket(usuario: Usuario) -> list[Pesaje]:
    return (Pesaje.query.outerjoin(Ticket, Ticket.numeroPesaje == Pesaje.idPesaje)
            .filter(Ticket.numeroTicket.is_(None), Pesaje.idUsuario == usuario.id)
            .order_by(Pesaje.idPesaje).all())
