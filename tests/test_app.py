from sqlalchemy import text

from app.extensions import db


def test_create_app_activa_foreign_keys(app):
    with app.app_context():
        assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1
