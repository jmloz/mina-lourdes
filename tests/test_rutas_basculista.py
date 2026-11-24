from datetime import date

from app.extensions import db
from app.models import Pesaje, Ticket
from app.servicios import bascula as svc_bascula
from app.servicios import pesajes as svc_pesajes
from app.servicios import tickets as svc_tickets


def _texto(r):
    return r.get_data(as_text=True)


def _pesaje_y_ticket(usuario, peso="25000.50"):
    p = svc_pesajes.registrar_pesaje(usuario, peso)
    return svc_tickets.emitir_ticket(usuario, p.idPesaje)


def _flujo_hasta_guardar(client):
    r = client.post("/basculista/captura", data={"accion": "leer"})
    assert "Lectura actual" in _texto(r)
    return client.post("/basculista/captura", data={"accion": "guardar"}, follow_redirects=True)


def test_flujo_pesaje_a_ticket(client, usuarios, login_como):
    login_como("basculista")
    r = _flujo_hasta_guardar(client)
    assert "Pesaje registrado" in _texto(r)
    pesaje = Pesaje.query.one()
    r = client.post("/basculista/generar", data={"idPesaje": pesaje.idPesaje},
                    follow_redirects=True)
    assert r.status_code == 200
    t = _texto(r)
    assert "T-0000" in t and "Pendiente" in t
    assert Ticket.query.count() == 1


def test_guardar_con_bascula_desconectada_muestra_error(client, usuarios, login_como):
    login_como("basculista")
    client.post("/basculista/captura", data={"accion": "leer"})
    svc_bascula.set_conexion(False)
    r = client.post("/basculista/captura", data={"accion": "guardar"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "No hay comunicación con la báscula" in _texto(r)
    assert Pesaje.query.count() == 0
    r = client.post("/basculista/captura", data={"accion": "leer"}, follow_redirects=True)
    assert r.status_code == 200
    assert "No hay comunicación con la báscula" in _texto(r)


def test_conexion_alterna(client, usuarios, login_como):
    login_como("basculista")
    client.post("/basculista/conexion")
    assert svc_bascula.obtener().estadoConexion == svc_bascula.DESCONECTADA
    client.post("/basculista/conexion")
    assert svc_bascula.obtener().estadoConexion == svc_bascula.CONECTADA


def test_doble_post_generar(client, usuarios, login_como):
    login_como("basculista")
    p = svc_pesajes.registrar_pesaje(usuarios["basculista"], "20000.00")
    client.post("/basculista/generar", data={"idPesaje": p.idPesaje})
    r = client.post("/basculista/generar", data={"idPesaje": p.idPesaje},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "ya tiene un ticket" in _texto(r)
    assert Ticket.query.count() == 1


def test_detalle_inexistente_404_amigable(client, usuarios, login_como):
    login_como("supervisor")
    r = client.get("/tickets/999999")
    assert r.status_code == 404
    assert "Ticket no encontrado" in _texto(r)


def test_consulta_filtro_fecha_invalida(client, usuarios, login_como):
    login_como("supervisor")
    r = client.get("/tickets/?desde=2026-13-01")
    assert r.status_code == 200
    assert "Formato de fecha inválido (AAAA-MM-DD)" in _texto(r)


def test_confirmacion_pesaje_muestra_datos(client, usuarios, login_como, monkeypatch):
    from decimal import Decimal
    monkeypatch.setattr(svc_bascula, "leer_peso", lambda rng=None: Decimal("23456.70"))
    login_como("basculista")
    client.post("/basculista/captura", data={"accion": "leer"})
    r = client.post("/basculista/captura", data={"accion": "guardar"}, follow_redirects=True)
    t = _texto(r)
    p = Pesaje.query.one()
    assert f"N.º de pesaje: {p.idPesaje}" in t
    assert "23,456.70" in t
    assert p.horaPesaje.strftime("%H:%M:%S") in t
    # refrescar la página no duplica el pesaje
    client.get("/basculista/captura")
    assert Pesaje.query.count() == 1


def test_guardar_ignora_peso_del_formulario(client, usuarios, login_como, monkeypatch):
    from decimal import Decimal
    monkeypatch.setattr(svc_bascula, "leer_peso", lambda rng=None: Decimal("30000.25"))
    login_como("basculista")
    r = client.post("/basculista/captura", data={"accion": "guardar", "peso": "12345.67"},
                    follow_redirects=True)
    assert "Primero lea el peso de la báscula" in _texto(r)
    assert Pesaje.query.count() == 0
    client.post("/basculista/captura", data={"accion": "leer"})
    client.post("/basculista/captura", data={"accion": "guardar", "peso": "12345.67"})
    assert Pesaje.query.one().peso == Decimal("30000.25")


def test_numeros_de_ticket_extremos(client, usuarios, login_como):
    login_como("supervisor")
    r = client.get("/tickets/99999999999999999999")
    assert r.status_code == 404 and "Ticket no encontrado" in _texto(r)
    assert client.get("/tickets/99999999999999999999/imprimir").status_code == 404
    r = client.get("/tickets/?numero=99999999999999999999")
    assert r.status_code == 200 and "Ticket no encontrado" in _texto(r)
    r = client.get("/tickets/?numero=²")
    assert r.status_code == 200 and "numérico" in _texto(r)


def test_formato_peso_no_numerico():
    from app.rutas.basculista import formato_peso
    assert formato_peso("abc") == "abc"


def test_consulta_lista_supervisor(client, usuarios, login_como):
    t1 = _pesaje_y_ticket(usuarios["basculista"])
    t2 = _pesaje_y_ticket(usuarios["basculista"], "21000.00")
    login_como("supervisor")
    t = _texto(client.get("/tickets/"))
    assert t1.folio in t and t2.folio in t
    assert "Pendiente de análisis" in t
    t = _texto(client.get(f"/tickets/?numero={t1.numeroTicket}"))
    assert t1.folio in t and t2.folio not in t
    t = _texto(client.get("/tickets/?estado=Ticket cerrado"))
    assert "No se encontraron tickets con esos filtros" in t


def test_consulta_sin_tickets(client, usuarios, login_como):
    login_como("supervisor")
    assert "No hay tickets registrados" in _texto(client.get("/tickets/"))


def test_basculista_solo_ve_sus_tickets(client, usuarios, login_como):
    propio = _pesaje_y_ticket(usuarios["basculista"])
    ajeno = _pesaje_y_ticket(usuarios["laboratorista"], "22000.00")
    login_como("basculista")
    t = _texto(client.get("/tickets/"))
    assert propio.folio in t and ajeno.folio not in t
    assert client.get(f"/tickets/{propio.numeroTicket}").status_code == 200
    assert client.get(f"/tickets/{ajeno.numeroTicket}").status_code == 403
    assert client.get(f"/tickets/{ajeno.numeroTicket}/imprimir").status_code == 403
    r = client.get(f"/tickets/{propio.numeroTicket}/imprimir")
    assert "Imprimir" in _texto(r) and "Cerrar" in _texto(r)


def test_roles_y_login(client, usuarios, login_como):
    assert client.get("/basculista/captura").status_code == 302
    login_como("supervisor")
    assert client.get("/basculista/captura").status_code == 403


def test_generar_id_pesaje_enorme_no_da_500(client, usuarios, login_como):
    login_como("basculista")
    for v in ("99999999999999999999", "9" * 5000, "0", "abc"):
        r = client.post("/basculista/generar", data={"idPesaje": v}, follow_redirects=True)
        assert r.status_code == 200 and "Seleccione un pesaje válido" in _texto(r)


def test_numero_ticket_gigante_no_da_500(client, usuarios, login_como):
    login_como("supervisor")
    r = client.get("/tickets/?numero=" + "9" * 5000)
    assert r.status_code == 200 and "Ticket no encontrado" in _texto(r)
    r = client.post("/supervisor/aprobaciones",
                    data={"accion": "aprobar", "numeroCorreccion": "9" * 5000},
                    follow_redirects=True)
    assert r.status_code == 200 and "Corrección no encontrada" in _texto(r)


def test_filtro_estado_opciones_y_mensajes(client, usuarios, login_como):
    login_como("supervisor")
    t = _texto(client.get("/tickets/"))
    assert "Ticket emitido</option>" not in t and "Corrección aprobada</option>" not in t
    assert "No hay tickets registrados" in t
    t = _texto(client.get("/tickets/?estado=Ticket cerrado"))
    assert "No se encontraron tickets con esos filtros" in t


def _desconectar(client):
    client.post("/basculista/conexion")


def test_flujo_manual_a_ticket(client, usuarios, login_como):
    login_como("basculista")
    _desconectar(client)
    r = client.post("/basculista/captura",
                    data={"accion": "guardar_manual", "peso_manual": "18500,25"},
                    follow_redirects=True)
    t = _texto(r)
    assert "Pesaje registrado" in t and "captura manual" in t and "18,500.25" in t
    pesaje = Pesaje.query.one()
    assert pesaje.lecturaValida is False
    r = client.post("/basculista/generar", data={"idPesaje": pesaje.idPesaje})
    r = client.get(r.headers["Location"])
    t = _texto(r)
    assert "Manual" in t and "18,500.25" in t


def test_guardar_manual_conectada_rechaza(client, usuarios, login_como):
    login_como("basculista")
    r = client.post("/basculista/captura",
                    data={"accion": "guardar_manual", "peso_manual": "100"},
                    follow_redirects=True)
    assert "La captura manual solo está disponible con la báscula desconectada" in _texto(r)
    assert Pesaje.query.count() == 0


def test_captura_muestra_modo(client, usuarios, login_como):
    login_como("basculista")
    t = _texto(client.get("/basculista/captura"))
    assert "Modo: Lectura de báscula" in t and "peso_manual" not in t
    _desconectar(client)
    t = _texto(client.get("/basculista/captura"))
    assert "Modo: Captura manual (báscula desconectada)" in t and 'name="peso_manual"' in t


def test_manual_texto_invalido_conserva_form(client, usuarios, login_como):
    login_como("basculista")
    _desconectar(client)
    r = client.post("/basculista/captura",
                    data={"accion": "guardar_manual", "peso_manual": "abc"})
    assert r.status_code == 200
    t = _texto(r)
    assert "debe ser un número" in t and 'value="abc"' in t
    assert Pesaje.query.count() == 0


def test_alternar_conexion_borra_lectura(client, usuarios, login_como):
    login_como("basculista")
    client.post("/basculista/captura", data={"accion": "leer"})
    client.post("/basculista/conexion")
    client.post("/basculista/conexion")
    r = client.post("/basculista/captura", data={"accion": "guardar"}, follow_redirects=True)
    assert "Primero lea el peso de la báscula" in _texto(r)
    assert Pesaje.query.count() == 0
