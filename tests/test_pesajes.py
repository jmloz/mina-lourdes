import random
from datetime import date
from decimal import Decimal

import pytest

from app.errores import ErrorBascula, ErrorValidacion
from app.extensions import db
from app.models import Bitacora, Pesaje, Usuario
from app.servicios import bascula, bitacora, pesajes


@pytest.fixture
def basculista(app):
    u = Usuario(nombre="Beto", usuario="beto", rol="basculista")
    u.set_password("x")
    db.session.add(u)
    db.session.commit()
    return u


def test_leer_peso_en_rango(app):
    p = bascula.leer_peso(random.Random(1))
    assert Decimal("15000") <= p <= Decimal("40000")
    assert p.as_tuple().exponent == -2


def test_leer_peso_desconectada_lanza_error(app):
    bascula.set_conexion(False)
    with pytest.raises(ErrorBascula, match="No hay comunicación con la báscula"):
        bascula.leer_peso()


def test_registrar_pesaje_guarda_y_escribe_bitacora(basculista):
    p = pesajes.registrar_pesaje(basculista, "25000.50")
    assert p.peso == Decimal("25000.50") and p.lecturaValida
    regs = Bitacora.query.all()
    assert len(regs) == 1 and regs[0].accion == "Registrar pesaje"
    assert regs[0].usuarioResponsable == "beto"
    assert pesajes.sin_ticket(basculista) == [p]


@pytest.mark.parametrize("peso", ["0", "-5", "80000.01", "abc", "", "1e30"])
def test_peso_invalido(basculista, peso):
    with pytest.raises(ErrorValidacion):
        pesajes.registrar_pesaje(basculista, peso)
    assert Pesaje.query.count() == 0


def test_peso_con_coma(basculista):
    p = pesajes.registrar_pesaje(basculista, "25000,5")
    assert p.peso == Decimal("25000.50")


def test_no_guarda_si_bascula_desconectada(basculista):
    bascula.set_conexion(False)
    with pytest.raises(ErrorBascula):
        pesajes.registrar_pesaje(basculista, "100")
    assert Pesaje.query.count() == 0


def test_bitacora_rango_invalido(app):
    with pytest.raises(ErrorValidacion, match="El rango de fechas no es válido"):
        bitacora.consultar(date(2026, 2, 1), date(2026, 1, 1), None, None)


def test_bitacora_filtra(basculista):
    bitacora.registrar(basculista, "A", "d")
    bitacora.registrar(None, "B", "d")
    db.session.commit()
    assert [b.accion for b in bitacora.consultar(None, None, "sistema", None)] == ["B"]
    assert len(bitacora.consultar(date.today(), date.today(), None, None)) == 2


def test_sin_ticket_solo_del_usuario(basculista):
    otro = Usuario(nombre="Otro", usuario="otro", rol="basculista")
    otro.set_password("x")
    db.session.add(otro)
    db.session.commit()
    mio = pesajes.registrar_pesaje(basculista, "100")
    pesajes.registrar_pesaje(otro, "200")
    assert pesajes.sin_ticket(basculista) == [mio]


def test_pesaje_manual_con_bascula_desconectada(basculista):
    bascula.set_conexion(False)
    p = pesajes.registrar_pesaje_manual(basculista, "18500,25")
    assert p.peso == Decimal("18500.25") and p.lecturaValida is False
    reg = Bitacora.query.one()
    assert reg.accion == "Captura manual"
    assert reg.detalleCambio == "Peso capturado manualmente: 18500.25 kg"


def test_pesaje_manual_con_bascula_conectada_rechaza(basculista):
    with pytest.raises(ErrorValidacion, match="solo está disponible con la báscula desconectada"):
        pesajes.registrar_pesaje_manual(basculista, "100")
    assert Pesaje.query.count() == 0


@pytest.mark.parametrize("peso", ["0", "-1", "80000.01", "abc", "", "1e30"])
def test_pesaje_manual_invalido(basculista, peso):
    bascula.set_conexion(False)
    with pytest.raises(ErrorValidacion):
        pesajes.registrar_pesaje_manual(basculista, peso)
    assert Pesaje.query.count() == 0


def test_sin_ticket_incluye_manual(basculista):
    bascula.set_conexion(False)
    p = pesajes.registrar_pesaje_manual(basculista, "100")
    assert pesajes.sin_ticket(basculista) == [p]
