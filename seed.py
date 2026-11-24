"""Datos demo de Mina Lourdes. Uso: python seed.py (borra y recrea la BD)."""
from app.extensions import db
from app.models import Ticket, Usuario
from app.servicios import analisis, bascula, correcciones, pesajes, tickets

USUARIOS = (
    ("basculista", "Carlos Mendoza Quispe", "basculista"),
    ("laboratorista", "Lucía Fernández Rojas", "laboratorista"),
    ("supervisor", "Ricardo Salazar Vega", "supervisor"),
)

# (peso kg, ley, observaciones, destino)
TICKETS = (
    ("24350.00", None, "", "PENDIENTE"),
    ("31820.50", None, "", "PENDIENTE"),
    ("18975.25", "2.450", "Muestra homogénea", "ANALISIS"),
    ("27640.00", "3.120", "", "ANALISIS"),
    ("22110.75", "1.875", "Presencia de humedad", "ACTUALIZADO"),
    ("35200.00", "2.960", "", "CERRADO"),
    ("29480.40", "4.015", "Alta ley, revisar", "CERRADO"),
    ("26730.00", "2.210", "", "EN_CORRECCION"),
)


def sembrar(db) -> None:
    for usuario, nombre, rol in USUARIOS:
        if Usuario.query.filter_by(usuario=usuario).first() is None:
            u = Usuario(nombre=nombre, usuario=usuario, rol=rol)
            u.set_password("1234")
            db.session.add(u)
    db.session.commit()
    bascula.obtener()
    if Ticket.query.count() > 0:
        return

    bas = Usuario.query.filter_by(usuario="basculista").one()
    lab = Usuario.query.filter_by(usuario="laboratorista").one()
    sup = Usuario.query.filter_by(usuario="supervisor").one()
    for peso, ley, obs, destino in TICKETS:
        t = tickets.emitir_ticket(bas, pesajes.registrar_pesaje(bas, peso).idPesaje)
        if ley is None:
            continue
        analisis.registrar_analisis(lab, t.numeroTicket, ley, obs)
        if destino == "ACTUALIZADO":
            c = correcciones.solicitar(sup, t.numeroTicket, "resultadoLey", "1.950",
                                       "Error de transcripción del resultado")
            correcciones.aprobar(sup, c.numeroCorreccion)
        elif destino == "CERRADO":
            tickets.cerrar_ticket(sup, t.numeroTicket)
        elif destino == "EN_CORRECCION":
            correcciones.solicitar(sup, t.numeroTicket, "resultadoLey", "2.310",
                                   "Se repitió el ensayo de laboratorio")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        sembrar(db)
        print("Base de datos demo creada: usuarios basculista/laboratorista/supervisor, clave 1234")
