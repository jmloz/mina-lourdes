from datetime import date, timedelta

import pytest

from app.errores import ErrorValidacion
from app.extensions import db
from app.estados import ANALISIS, CERRADO, PENDIENTE
from app.models import Bitacora, Ticket, Usuario
from app.servicios import pesajes, tickets


@pytest.fixture
def basculista(app):
    u = Usuario(nombre="Beto", usuario="beto", rol="basculista")
    u.set_password("x")
    db.session.add(u)
    db.session.commit()
    return u


def _ticket(u, peso="25000.00"):
    p = pesajes.registrar_pesaje(u, peso)
    return tickets.emitir_ticket(u, p.idPesaje)


def test_emitir_ticket_queda_pendiente(basculista):
    t = _ticket(basculista)
    assert t.estadoTicket == PENDIENTE
    detalles = [(b.accion, b.detalleCambio) for b in Bitacora.query.all()]
    assert any(a == "Emitir ticket" for a, _ in detalles)
    assert ("Cambio de estado", "Ticket emitido → Pendiente de análisis") in detalles


def test_emitir_dos_veces_rechaza(basculista):
    p = pesajes.registrar_pesaje(basculista, "100")
    tickets.emitir_ticket(basculista, p.idPesaje)
    with pytest.raises(ErrorValidacion, match="El pesaje ya tiene un ticket"):
        tickets.emitir_ticket(basculista, p.idPesaje)
    assert Ticket.query.count() == 1


def test_emitir_pesaje_inexistente(basculista):
    with pytest.raises(ErrorValidacion, match="El pesaje ya tiene un ticket"):
        tickets.emitir_ticket(basculista, 999)


def test_buscar_por_estado_y_numero(basculista):
    t1 = _ticket(basculista)
    t2 = _ticket(basculista)
    t2.estadoTicket = ANALISIS
    db.session.commit()
    assert [t.numeroTicket for t in tickets.buscar()] == [t2.numeroTicket, t1.numeroTicket]
    assert tickets.buscar(estado=ANALISIS) == [t2]
    assert tickets.buscar(numero=t1.numeroTicket) == [t1]
    assert tickets.buscar(idUsuario=basculista.id + 99) == []


def test_buscar_rango_fechas(basculista):
    t = _ticket(basculista)
    hoy = date.today()
    assert tickets.buscar(desde=hoy, hasta=hoy) == [t]
    assert tickets.buscar(desde=hoy + timedelta(days=1)) == []
    with pytest.raises(ErrorValidacion, match="El rango de fechas no es válido"):
        tickets.buscar(desde=hoy, hasta=hoy - timedelta(days=1))


def test_ultimos_limite(basculista):
    for _ in range(3):
        _ticket(basculista)
    r = tickets.ultimos(2)
    assert len(r) == 2 and r[0].numeroTicket > r[1].numeroTicket


def test_cerrar_desde_pendiente_rechaza(basculista):
    t = _ticket(basculista)
    with pytest.raises(ErrorValidacion, match="Transición no permitida"):
        tickets.cerrar_ticket(basculista, t.numeroTicket)
    assert t.estadoTicket == PENDIENTE


def test_cerrar_desde_analisis(basculista):
    t = _ticket(basculista)
    t.estadoTicket = ANALISIS
    db.session.commit()
    assert tickets.cerrar_ticket(basculista, t.numeroTicket).estadoTicket == CERRADO


def test_obtener_inexistente(app):
    with pytest.raises(ErrorValidacion, match="Ticket no encontrado"):
        tickets.obtener(123)
