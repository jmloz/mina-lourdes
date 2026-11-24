import random
from decimal import Decimal

from app.errores import ErrorBascula
from app.extensions import db
from app.models import Bascula

CONECTADA = "Conectada"
DESCONECTADA = "Desconectada"


def obtener() -> Bascula:
    b = db.session.get(Bascula, 1)
    if b is None:
        b = Bascula(idBascula=1, estadoConexion=CONECTADA)
        db.session.add(b)
        db.session.commit()
    return b


def set_conexion(conectada: bool) -> None:
    obtener().estadoConexion = CONECTADA if conectada else DESCONECTADA
    db.session.commit()


def leer_peso(rng: random.Random | None = None) -> Decimal:
    if obtener().estadoConexion != CONECTADA:
        raise ErrorBascula("No hay comunicación con la báscula")
    rng = rng or random
    centavos = rng.randint(1500000, 4000000)
    return Decimal(centavos).scaleb(-2).quantize(Decimal("0.01"))
