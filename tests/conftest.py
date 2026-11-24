import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    return db.session


DEMO_USUARIOS = (
    ("basculista", "Carlos Mendoza Quispe", "basculista"),
    ("laboratorista", "Lucía Fernández Rojas", "laboratorista"),
    ("supervisor", "Ricardo Salazar Vega", "supervisor"),
)


@pytest.fixture
def usuarios(app):
    from app.models import Usuario
    res = {}
    for usuario, nombre, rol in DEMO_USUARIOS:
        u = Usuario(nombre=nombre, usuario=usuario, rol=rol)
        u.set_password("1234")
        db.session.add(u)
        res[rol] = u
    db.session.commit()
    return res


@pytest.fixture
def login_como(client):
    def _login(usuario: str, password: str = "1234"):
        return client.post("/login", data={"usuario": usuario, "password": password})
    return _login
