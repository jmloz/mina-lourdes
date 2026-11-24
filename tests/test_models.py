import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.estados import ANALISIS, CERRADO, EN_CORRECCION, PENDIENTE, puede_transicionar
from app.models import Analisis, Bascula, Pesaje, Ticket, Usuario


def _base(db_session):
    u = Usuario(nombre="Bas", usuario="bas", rol="basculista")
    u.set_password("1234")
    b = Bascula(estadoConexion="Conectada")
    db_session.add_all([u, b])
    db_session.commit()
    p = Pesaje(peso=20000, fechaPesaje=datetime.date.today(),
               horaPesaje=datetime.time(10, 0), lecturaValida=True,
               idBascula=b.idBascula, idUsuario=u.id)
    db_session.add(p)
    db_session.commit()
    return u, p


def _ticket(u, p):
    return Ticket(fechaEmision=datetime.date.today(), estadoTicket=PENDIENTE,
                  numeroPesaje=p.idPesaje, idUsuario=u.id)


def test_pesaje_no_admite_dos_tickets(db_session):
    u, p = _base(db_session)
    db_session.add(_ticket(u, p))
    db_session.commit()
    db_session.add(_ticket(u, p))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_ticket_no_admite_dos_analisis(db_session):
    u, p = _base(db_session)
    t = _ticket(u, p)
    db_session.add(t)
    db_session.commit()
    for _ in range(2):
        db_session.add(Analisis(fechaAnalisis=datetime.date.today(), resultadoLey=1.5,
                                observaciones="", numeroTicket=t.numeroTicket, idUsuario=u.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_folio_formato():
    assert Ticket(numeroTicket=123).folio == "T-000123"


def test_transiciones():
    assert puede_transicionar(PENDIENTE, ANALISIS)
    assert not puede_transicionar(CERRADO, EN_CORRECCION)
    assert not puede_transicionar(PENDIENTE, EN_CORRECCION)


def test_password_hash():
    u = Usuario(nombre="x", usuario="x", rol="supervisor")
    u.set_password("1234")
    assert u.check_password("1234")
    assert not u.check_password("x")
    assert u.password_hash != "1234"
