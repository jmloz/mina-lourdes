EMITIDO = "Ticket emitido"
PENDIENTE = "Pendiente de análisis"
ANALISIS = "Análisis registrado"
EN_CORRECCION = "En corrección"
APROBADA = "Corrección aprobada"
ACTUALIZADO = "Ticket actualizado"
CERRADO = "Ticket cerrado"

TRANSICIONES: dict[str, set[str]] = {
    EMITIDO: {PENDIENTE},
    PENDIENTE: {ANALISIS},
    ANALISIS: {EN_CORRECCION, CERRADO},
    EN_CORRECCION: {APROBADA, ANALISIS, ACTUALIZADO},
    APROBADA: {ACTUALIZADO},
    ACTUALIZADO: {EN_CORRECCION, CERRADO},
    CERRADO: set(),
}


def puede_transicionar(actual: str, nuevo: str) -> bool:
    return nuevo in TRANSICIONES.get(actual, set())
