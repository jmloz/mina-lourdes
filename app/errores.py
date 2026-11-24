class ErrorValidacion(Exception):
    """Error de regla de negocio; el mensaje (en español) se muestra al usuario."""


class ErrorBascula(ErrorValidacion):
    """Falla de la báscula (desconectada o lectura inválida)."""
