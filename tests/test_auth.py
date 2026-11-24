from app.auth import login_requerido
from app.extensions import db
from app.models import Bitacora, Usuario
from seed import sembrar


def test_login_correcto_muestra_menu_por_rol(client, usuarios, login_como):
    r = login_como("basculista")
    assert r.status_code == 302
    html = client.get("/").get_data(as_text=True)
    assert "Captura de pesaje" in html
    assert "Bitácora" not in html
    assert Bitacora.query.filter_by(accion="Iniciar sesión", usuarioResponsable="basculista").count() == 1


def test_login_incorrecto(client, usuarios, login_como):
    r = login_como("basculista", "mala")
    assert "Usuario o contraseña incorrectos" in r.get_data(as_text=True)
    assert client.get("/").status_code == 302


def test_sin_sesion_redirige(client, usuarios):
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_basculista_en_ruta_supervisor_403(app, client, usuarios, login_como):
    @app.route("/solo-supervisor")
    @login_requerido("supervisor")
    def solo_supervisor():
        return "ok"

    login_como("basculista")
    assert client.get("/solo-supervisor").status_code == 403
    client.get("/logout")
    login_como("supervisor")
    assert client.get("/solo-supervisor").status_code == 200


def test_seed_idempotente(app):
    sembrar(db)
    sembrar(db)
    assert Usuario.query.count() == 3


def test_error_validacion_no_redirige_a_referer_externo(app, client):
    from app.errores import ErrorValidacion

    @app.route("/falla")
    def falla():
        raise ErrorValidacion("Dato inválido")

    r = client.get("/falla", headers={"Referer": "http://evil.example/x"})
    assert r.status_code == 302 and r.headers["Location"] == "/"
    r = client.get("/falla", headers={"Referer": "http://localhost/basculista/captura"})
    assert r.headers["Location"] == "http://localhost/basculista/captura"


def test_seed_correcciones_solicitadas_por_supervisor(app):
    from app.models import CorreccionTicket, Ticket
    sembrar(db)
    cs = CorreccionTicket.query.all()
    assert cs and all(c.solicitante.rol == "supervisor" for c in cs)
    estados = [t.estadoTicket for t in Ticket.query.all()]
    assert estados.count("Ticket cerrado") == 2 and estados.count("En corrección") == 1
    assert estados.count("Ticket actualizado") == 1
