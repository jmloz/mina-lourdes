from app.estados import ANALISIS
from app.extensions import db
from app.models import Analisis, Ticket
from app.servicios import analisis as svc_analisis
from app.servicios import pesajes as svc_pesajes
from app.servicios import tickets as svc_tickets


def _texto(r):
    return r.get_data(as_text=True)


def _ticket(usuarios, peso="25000.50"):
    u = usuarios["basculista"]
    p = svc_pesajes.registrar_pesaje(u, peso)
    return svc_tickets.emitir_ticket(u, p.idPesaje)


def test_historial_vacio_mensaje(client, usuarios, login_como):
    login_como("laboratorista")
    r = client.get("/laboratorio/historial")
    assert r.status_code == 200
    assert "No se encontraron registros" in _texto(r)


def test_historial_lista_con_accion_solo_pendientes(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("laboratorista")
    assert "Registrar análisis" in _texto(client.get("/laboratorio/historial"))
    svc_analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "1.5")
    r = client.get("/laboratorio/historial")
    assert t.folio in _texto(r) and "/laboratorio/analisis/" not in _texto(r)


def test_registrar_analisis_desde_historial(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("laboratorista")
    r = client.get(f"/laboratorio/analisis/{t.numeroTicket}")
    assert "Guardar análisis" in _texto(r)
    r = client.post(f"/laboratorio/analisis/{t.numeroTicket}",
                    data={"resultadoLey": "2.345", "observaciones": "ok"},
                    follow_redirects=True)
    assert "Análisis registrado" in _texto(r) and "2.345" in _texto(r)
    assert db.session.get(Ticket, t.numeroTicket).estadoTicket == ANALISIS
    assert Analisis.query.count() == 1


def test_ley_texto_invalido_muestra_error_y_conserva_form(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("laboratorista")
    r = client.post(f"/laboratorio/analisis/{t.numeroTicket}",
                    data={"resultadoLey": "abc", "observaciones": "mi nota"})
    assert r.status_code == 200
    assert 'value="abc"' in _texto(r) and "mi nota" in _texto(r)
    assert Analisis.query.count() == 0


def test_ticket_no_pendiente_sin_formulario(client, usuarios, login_como):
    t = _ticket(usuarios)
    svc_analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "1.5")
    login_como("laboratorista")
    r = client.get(f"/laboratorio/analisis/{t.numeroTicket}")
    assert "Guardar análisis" not in _texto(r)


def test_ticket_inexistente_404(client, usuarios, login_como):
    login_como("laboratorista")
    assert client.get("/laboratorio/analisis/99").status_code == 404
    assert client.get(f"/laboratorio/analisis/{2**31}").status_code == 404


def test_supervisor_no_puede_registrar_analisis_403(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("supervisor")
    assert client.get(f"/laboratorio/analisis/{t.numeroTicket}").status_code == 403
    assert client.post(f"/laboratorio/analisis/{t.numeroTicket}",
                       data={"resultadoLey": "1"}).status_code == 403
    assert client.get("/laboratorio/historial").status_code == 403


def test_detalle_muestra_resultado_analisis(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("laboratorista")
    r = client.get(f"/tickets/{t.numeroTicket}")
    assert "Resultado de análisis" in _texto(r) and "Pendiente" in _texto(r)
    svc_analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "3.1", "muestra A")
    r = client.get(f"/tickets/{t.numeroTicket}")
    s = _texto(r)
    assert "Resultado de análisis" in s and "3.100 %" in s and "muestra A" in s
