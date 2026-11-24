from decimal import Decimal

import pytest

from app.errores import ErrorValidacion
from app.estados import ANALISIS, PENDIENTE
from app.extensions import db
from app.models import Bitacora, Usuario
from app.servicios import analisis, pesajes, tickets


@pytest.fixture
def usuarios(app):
    out = {}
    for rol, nom in (("basculista", "beto"), ("laboratorista", "lola")):
        u = Usuario(nombre=nom, usuario=nom, rol=rol)
        u.set_password("x")
        db.session.add(u)
        out[rol] = u
    db.session.commit()
    return out


def _ticket(u):
    p = pesajes.registrar_pesaje(u, "25000.00")
    return tickets.emitir_ticket(u, p.idPesaje)


def test_registrar_analisis_cambia_estado(usuarios):
    t = _ticket(usuarios["basculista"])
    a = analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "3.25", "ok")
    assert a.resultadoLey == Decimal("3.250")
    assert a.observaciones == "ok"
    assert t.estadoTicket == ANALISIS
    assert Bitacora.query.filter_by(accion="Registrar análisis").count() == 1


def test_analisis_ticket_no_pendiente_rechaza(usuarios):
    t = _ticket(usuarios["basculista"])
    analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "3")
    with pytest.raises(ErrorValidacion):
        analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "3")


@pytest.mark.parametrize("ley", ["-0.001", "100.001", "x", ""])
def test_ley_invalida(usuarios, ley):
    t = _ticket(usuarios["basculista"])
    with pytest.raises(ErrorValidacion):
        analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, ley)
    assert t.estadoTicket == PENDIENTE


def test_ley_con_coma(usuarios):
    t = _ticket(usuarios["basculista"])
    a = analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "3,25")
    assert a.resultadoLey == Decimal("3.250")


def test_observaciones_largas_rechaza(usuarios):
    t = _ticket(usuarios["basculista"])
    with pytest.raises(ErrorValidacion):
        analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "3", "x" * 256)
