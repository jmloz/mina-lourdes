"""Arranque de Mina Lourdes: crea la BD demo si falta y levanta el servidor en 127.0.0.1:5000."""
import os

from app import create_app
from app.extensions import db
from app.models import Usuario
from seed import sembrar

app = create_app()

if __name__ == "__main__":
    ruta_bd = os.path.join(app.instance_path, "mina_lourdes.db")
    existia = os.path.exists(ruta_bd)
    with app.app_context():
        db.create_all()
        if not existia or Usuario.query.count() == 0:
            sembrar(db)
            print("Datos demo creados: basculista / laboratorista / supervisor, clave 1234")
    app.run(host="127.0.0.1", port=5000, debug=False)
