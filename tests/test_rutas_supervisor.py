from app.estados import ACTUALIZADO, ANALISIS, CERRADO
from app.extensions import db
from app.models import Ticket
from app.servicios import analisis as svc_analisis
from app.servicios import correcciones as svc_corr
from app.servicios import pesajes as svc_pesajes
from app.servicios import tickets as svc_tickets


def _texto(r):
    return r.get_data(as_text=True)


def _ticket(usuarios, peso="25000.50"):
    u = usuarios["basculista"]
    p = svc_pesajes.registrar_pesaje(u, peso)
    t = svc_tickets.emitir_ticket(u, p.idPesaje)
    svc_analisis.registrar_analisis(usuarios["laboratorista"], t.numeroTicket, "1.5")
    return t


def _solicitar(client, t, valor="26000", motivo="Error de captura", campo="peso"):
    return client.post(f"/supervisor/correccion/{t.numeroTicket}",
                       data={"campo": campo, "valorNuevo": valor, "motivo": motivo},
                       follow_redirects=True)


def test_flujo_correccion_aprobada(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("supervisor")
    r = client.get(f"/supervisor/correccion/{t.numeroTicket}")
    assert "Enviar solicitud" in _texto(r) and "Valor actual" in _texto(r)
    r = _solicitar(client, t)
    assert "Solicitud de corrección enviada" in _texto(r)
    r = client.get("/supervisor/aprobaciones")
    assert "Error de captura" in _texto(r) and "25,000.50 kg" in _texto(r) and "26,000.00 kg" in _texto(r)
    r = client.post("/supervisor/aprobaciones",
                    data={"accion": "aprobar", "numeroCorreccion": "1"}, follow_redirects=True)
    assert r.status_code == 200
    r = client.get(f"/tickets/{t.numeroTicket}")
    assert "26,000.00" in _texto(r) or "26000" in _texto(r)
    assert ACTUALIZADO in _texto(r)
    r = client.get("/supervisor/bitacora")
    assert "Aprobar corrección" in _texto(r)


def test_flujo_correccion_rechazada(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("supervisor")
    _solicitar(client, t)
    r = client.post("/supervisor/aprobaciones",
                    data={"accion": "rechazar", "numeroCorreccion": "1"}, follow_redirects=True)
    assert "rechazada" in _texto(r)
    assert db.session.get(Ticket, t.numeroTicket).estadoTicket == ANALISIS
    assert "Rechazar corrección" in _texto(client.get("/supervisor/bitacora"))


def test_correccion_error_conserva_valores(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("supervisor")
    r = client.post(f"/supervisor/correccion/{t.numeroTicket}",
                    data={"campo": "peso", "valorNuevo": "abc", "motivo": "mi motivo"})
    assert r.status_code == 200
    assert 'value="abc"' in _texto(r) and "mi motivo" in _texto(r)


def test_accion_invalida_y_id_malo_no_500(client, usuarios, login_como):
    _ticket(usuarios)
    login_como("supervisor")
    for d in ({"accion": "x", "numeroCorreccion": "1"},
              {"accion": "aprobar", "numeroCorreccion": "abc"},
              {"accion": "aprobar", "numeroCorreccion": "99999999999"},
              {"accion": "aprobar", "numeroCorreccion": "5"}, {}):
        r = client.post("/supervisor/aprobaciones", data=d, follow_redirects=True)
        assert r.status_code == 200
    assert client.get("/supervisor/correccion/99999999999").status_code == 404
    assert client.post("/supervisor/cerrar/99999999999").status_code == 404


def test_cerrar_ticket(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("supervisor")
    assert "Cerrar ticket" in _texto(client.get(f"/tickets/{t.numeroTicket}"))
    r = client.post(f"/supervisor/cerrar/{t.numeroTicket}", follow_redirects=True)
    assert CERRADO in _texto(r)
    assert db.session.get(Ticket, t.numeroTicket).estadoTicket == CERRADO
    assert "Cerrar ticket" not in _texto(client.get(f"/tickets/{t.numeroTicket}"))


def test_botones_solo_supervisor(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("laboratorista")
    assert "Solicitar corrección" not in _texto(client.get(f"/tickets/{t.numeroTicket}"))
    assert client.post(f"/supervisor/cerrar/{t.numeroTicket}").status_code == 403


def test_bitacora_rango_invertido_mensaje(client, usuarios, login_como):
    login_como("supervisor")
    r = client.get("/supervisor/bitacora?desde=2026-02-01&hasta=2026-01-01")
    assert r.status_code == 200 and "El rango de fechas no es válido" in _texto(r)


def test_bitacora_fecha_mal_formada_mensaje(client, usuarios, login_como):
    login_como("supervisor")
    r = client.get("/supervisor/bitacora?desde=31/12/2026")
    assert r.status_code == 200 and "Formato de fecha inválido (AAAA-MM-DD)" in _texto(r)


def test_bitacora_muestra_columnas(client, usuarios, login_como):
    t = _ticket(usuarios)
    login_como("supervisor")
    _solicitar(client, t)
    r = client.get("/supervisor/bitacora")
    txt = _texto(r)
    for col in ("Fecha-hora", "Usuario", "Acción", "Detalle", "Ticket"):
        assert col in txt
    assert "Solicitar corrección" in txt and t.folio in txt and "supervisor" in txt
    r = client.get("/supervisor/bitacora?usuario=nadie")
    assert "<td>Solicitar corrección</td>" not in _texto(r)


def test_laboratorista_bitacora_403(client, usuarios, login_como):
    login_como("laboratorista")
    assert client.get("/supervisor/bitacora").status_code == 403
    assert client.get("/supervisor/aprobaciones").status_code == 403
