from decimal import Decimal, InvalidOperation

from app.errores import ErrorValidacion


def parse_decimal(texto: str, campo: str, minimo: Decimal, maximo: Decimal,
                  decimales: int, minimo_exclusivo: bool = False) -> Decimal:
    if isinstance(texto, Decimal):
        texto = str(texto)
    texto = (texto or "").strip().replace(",", ".")
    if not texto:
        raise ErrorValidacion(f"El {campo} es obligatorio")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ErrorValidacion(f"El {campo} debe ser un número") from None
    if not valor.is_finite():
        raise ErrorValidacion(f"El {campo} debe ser un número")
    def fuera(v: Decimal) -> bool:
        return (v <= minimo if minimo_exclusivo else v < minimo) or v > maximo

    msg = f"El {campo} debe estar entre {minimo} y {maximo}"
    if fuera(valor):
        raise ErrorValidacion(msg)
    valor = valor.quantize(Decimal(1).scaleb(-decimales))
    if fuera(valor):
        raise ErrorValidacion(msg)
    return valor
