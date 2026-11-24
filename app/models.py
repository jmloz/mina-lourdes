from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

ROLES = ("basculista", "laboratorista", "supervisor")
ESTADOS_CORRECCION = ("pendiente", "aprobada", "rechazada")


class Usuario(db.Model):
    __tablename__ = "usuario"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        db.CheckConstraint("rol IN ('basculista','laboratorista','supervisor')", name="ck_usuario_rol"),
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Bascula(db.Model):
    __tablename__ = "bascula"
    idBascula = db.Column(db.Integer, primary_key=True)
    estadoConexion = db.Column(db.String(20), nullable=False, default="Conectada")  # Conectada/Desconectada


class Pesaje(db.Model):
    __tablename__ = "pesaje"
    idPesaje = db.Column(db.Integer, primary_key=True)
    peso = db.Column(db.Numeric(10, 2, asdecimal=True), nullable=False)
    fechaPesaje = db.Column(db.Date, nullable=False)
    horaPesaje = db.Column(db.Time, nullable=False)
    lecturaValida = db.Column(db.Boolean, nullable=False, default=True)
    idBascula = db.Column(db.Integer, db.ForeignKey("bascula.idBascula"), nullable=False)
    idUsuario = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)

    bascula = db.relationship("Bascula")
    usuario = db.relationship("Usuario")
    ticket = db.relationship("Ticket", back_populates="pesaje", uselist=False)


class Ticket(db.Model):
    __tablename__ = "ticket"
    numeroTicket = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fechaEmision = db.Column(db.Date, nullable=False)
    estadoTicket = db.Column(db.String(30), nullable=False)
    estadoPrevio = db.Column(db.String(30), nullable=True)
    numeroPesaje = db.Column(db.Integer, db.ForeignKey("pesaje.idPesaje"), unique=True, nullable=False)
    idUsuario = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)

    pesaje = db.relationship("Pesaje", back_populates="ticket")
    usuario = db.relationship("Usuario")
    analisis = db.relationship("Analisis", back_populates="ticket", uselist=False)
    correcciones = db.relationship("CorreccionTicket", back_populates="ticket",
                                   order_by="CorreccionTicket.numeroCorreccion")

    @property
    def folio(self) -> str:
        return f"T-{self.numeroTicket:06d}"


class Analisis(db.Model):
    __tablename__ = "analisis"
    numeroAnalisis = db.Column(db.Integer, primary_key=True)
    fechaAnalisis = db.Column(db.Date, nullable=False)
    resultadoLey = db.Column(db.Numeric(8, 3, asdecimal=True), nullable=False)
    observaciones = db.Column(db.String(255))
    numeroTicket = db.Column(db.Integer, db.ForeignKey("ticket.numeroTicket"), unique=True, nullable=False)
    idUsuario = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)

    ticket = db.relationship("Ticket", back_populates="analisis")
    usuario = db.relationship("Usuario")


class CorreccionTicket(db.Model):
    __tablename__ = "correccion_ticket"
    numeroCorreccion = db.Column(db.Integer, primary_key=True)
    numeroTicket = db.Column(db.Integer, db.ForeignKey("ticket.numeroTicket"), nullable=False)
    campo = db.Column(db.String(30), nullable=False)
    valorAnterior = db.Column(db.String(255))
    valorNuevo = db.Column(db.String(255))
    motivo = db.Column(db.String(255), nullable=False)
    estadoCorreccion = db.Column(db.String(20), nullable=False, default="pendiente")
    fechaSolicitud = db.Column(db.Date, nullable=False)
    fechaResolucion = db.Column(db.Date, nullable=True)
    idSolicitante = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    idRevisor = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)

    ticket = db.relationship("Ticket", back_populates="correcciones")
    solicitante = db.relationship("Usuario", foreign_keys=[idSolicitante])
    revisor = db.relationship("Usuario", foreign_keys=[idRevisor])

    __table_args__ = (
        db.CheckConstraint("estadoCorreccion IN ('pendiente','aprobada','rechazada')",
                           name="ck_correccion_estado"),
    )


class Bitacora(db.Model):
    __tablename__ = "bitacora"
    idBitacora = db.Column(db.Integer, primary_key=True)
    usuarioResponsable = db.Column(db.String(50), nullable=False)
    fechaHoraB = db.Column(db.DateTime, nullable=False)
    accion = db.Column(db.String(50), nullable=False)
    detalleCambio = db.Column(db.String(255))
    numeroTicket = db.Column(db.Integer, db.ForeignKey("ticket.numeroTicket"), nullable=True)
    numeroCorreccion = db.Column(db.Integer, db.ForeignKey("correccion_ticket.numeroCorreccion"), nullable=True)
