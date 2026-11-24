import os
import sqlite3
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import event
from werkzeug.exceptions import NotFound
from sqlalchemy.engine import Engine

from app.errores import ErrorValidacion
from app.extensions import db


@event.listens_for(Engine, "connect")
def _activar_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY="mina-lourdes-demo",
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "mina_lourdes.db"),
    )
    if config:
        app.config.from_mapping(config)

    db.init_app(app)
    from app import models  # noqa: F401  (registra las tablas para create_all)

    from app.auth import usuario_actual
    from app.rutas import principal
    from app.rutas import basculista, laboratorio, supervisor, tickets
    app.register_blueprint(principal.bp)
    app.register_blueprint(basculista.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(laboratorio.bp)
    app.register_blueprint(supervisor.bp)

    @app.context_processor
    def _contexto():
        return {"usuario": usuario_actual()}

    @app.errorhandler(403)
    def _prohibido(e):
        return render_template("error.html", codigo=403,
                               mensaje="No tiene permiso para acceder a esta pantalla."), 403

    @app.errorhandler(404)
    def _no_encontrado(e):
        mensaje = "La página solicitada no existe."
        if e.description and e.description != NotFound.description:
            mensaje = e.description
        return render_template("error.html", codigo=404, mensaje=mensaje), 404

    @app.errorhandler(ErrorValidacion)
    def _error_validacion(e):
        db.session.rollback()
        flash(str(e), "error")
        destino = url_for("principal.menu")
        ref = urlparse(request.referrer or "")
        if ref.scheme in ("http", "https") and ref.netloc == request.host:
            destino = request.referrer
        return redirect(destino)

    return app
