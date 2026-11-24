from decimal import Decimal

import pytest

from app.errores import ErrorValidacion
from app.estados import ACTUALIZADO, ANALISIS, CERRADO, EN_CORRECCION, PENDIENTE
from app.extensions import db
from app.models import Bitacora, Usuario
from app.servicios import analisis, correcciones, pesajes, tickets


@pytest.fixture
def us(app):
    out = {}
    for rol, nom in (("basculista", "beto"), ("laboratorista", "lola"), ("supervisor", "sam")):
        u = Usuario(nombre=nom, usuario=nom, rol=rol)
        u.set_password("x")
        db.session.add(u)
        out[rol] = u
    db.session.commit()
    return out


def _ticket_analisis(us):
    p = pesajes.registrar_pesaje(us["basculista"], "25000.00")
    t = tickets.emitir_ticket(us["basculista"], p.idPesaje)
    analisis.registrar_analisis(us["laboratorista"], t.numeroTicket, "3.25", "ok")
    return t


def test_solicitar_y_aprobar_peso(us):
    t = _ticket_analisis(us)
    c = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "24000,50", "error de captura")
    assert t.estadoTicket == EN_CORRECCION
    assert c.valorAnterior == "25000.00" and c.valorNuevo == "24000.50"
    assert correcciones.pendientes() == [c]
    correcciones.aprobar(us["supervisor"], c.numeroCorreccion)
    assert t.pesaje.peso == Decimal("24000.50")
    assert t.estadoTicket == ACTUALIZADO
    assert c.estadoCorreccion == "aprobada" and c.idRevisor == us["supervisor"].id
    assert c.fechaResolucion is not None
    detalles = [(b.accion, b.detalleCambio) for b in Bitacora.query.all()]
    assert ("Aprobar corrección", "peso: 25000.00 → 24000.50") in detalles
    assert any("Corrección aprobada" in d for _, d in detalles)
    assert correcciones.pendientes() == []


def test_aprobar_ley_y_observaciones(us):
    t = _ticket_analisis(us)
    c = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "resultadoLey", "4.5", "m")
    correcciones.aprobar(us["supervisor"], c.numeroCorreccion)
    assert t.analisis.resultadoLey == Decimal("4.500")
    c = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "observaciones", "nuevo", "m")
    correcciones.aprobar(us["supervisor"], c.numeroCorreccion)
    assert t.analisis.observaciones == "nuevo"


def test_valor_invalido_rechaza(us):
    t = _ticket_analisis(us)
    with pytest.raises(ErrorValidacion):
        correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "80000.01", "m")
    with pytest.raises(ErrorValidacion):
        correcciones.solicitar(us["laboratorista"], t.numeroTicket, "resultadoLey", "101", "m")
    assert t.estadoTicket == ANALISIS


def test_rechazar_restaura_estado_previo(us):
    t = _ticket_analisis(us)
    c = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "100", "m")
    correcciones.aprobar(us["supervisor"], c.numeroCorreccion)
    c2 = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "200", "m")
    correcciones.rechazar(us["supervisor"], c2.numeroCorreccion)
    assert t.estadoTicket == ACTUALIZADO
    assert t.pesaje.peso == Decimal("100.00")
    assert c2.estadoCorreccion == "rechazada"
    assert Bitacora.query.filter_by(accion="Rechazar corrección").count() == 1


def test_rechazar_desde_analisis(us):
    t = _ticket_analisis(us)
    c = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "100", "m")
    correcciones.rechazar(us["supervisor"], c.numeroCorreccion)
    assert t.estadoTicket == ANALISIS
    assert t.pesaje.peso == Decimal("25000.00")


def test_rechazo_tras_ciclo_aprobado(us):
    t = _ticket_analisis(us)
    c = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "100", "m")
    correcciones.aprobar(us["supervisor"], c.numeroCorreccion)
    c2 = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "200", "m")
    correcciones.rechazar(us["supervisor"], c2.numeroCorreccion)
    assert t.estadoTicket == ACTUALIZADO


def test_resolver_no_pendiente_rechaza(us):
    t = _ticket_analisis(us)
    c = correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "100", "m")
    correcciones.rechazar(us["supervisor"], c.numeroCorreccion)
    with pytest.raises(ErrorValidacion):
        correcciones.aprobar(us["supervisor"], c.numeroCorreccion)
    with pytest.raises(ErrorValidacion):
        correcciones.rechazar(us["supervisor"], c.numeroCorreccion)
    with pytest.raises(ErrorValidacion):
        correcciones.aprobar(us["supervisor"], 999)


@pytest.mark.parametrize("motivo", ["", "   "])
def test_solicitar_sin_motivo(us, motivo):
    t = _ticket_analisis(us)
    with pytest.raises(ErrorValidacion):
        correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "100", motivo)


def test_solicitar_en_pendiente_de_analisis_rechaza(us):
    p = pesajes.registrar_pesaje(us["basculista"], "100")
    t = tickets.emitir_ticket(us["basculista"], p.idPesaje)
    assert t.estadoTicket == PENDIENTE
    with pytest.raises(ErrorValidacion):
        correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "50", "m")


def test_solicitar_con_otra_pendiente_rechaza(us):
    t = _ticket_analisis(us)
    correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "100", "m")
    with pytest.raises(ErrorValidacion):
        correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "200", "m")


def test_solicitar_en_cerrado_rechaza(us):
    t = _ticket_analisis(us)
    tickets.cerrar_ticket(us["supervisor"], t.numeroTicket)
    assert t.estadoTicket == CERRADO
    with pytest.raises(ErrorValidacion):
        correcciones.solicitar(us["laboratorista"], t.numeroTicket, "peso", "100", "m")


def test_campo_desconocido_rechaza(us):
    t = _ticket_analisis(us)
    with pytest.raises(ErrorValidacion):
        correcciones.solicitar(us["laboratorista"], t.numeroTicket, "fecha", "x", "m")
