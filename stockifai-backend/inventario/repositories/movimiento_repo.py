from django.db import IntegrityError
from .base import DuplicateError
from inventario.models import Movimiento, StockPorDeposito
class MovimientoRepo:
    def crear_unico(self, spd: StockPorDeposito, *, tipo: str, cantidad: int, fecha, externo_id: str | None, documento: str | None=None) -> Movimiento:
        mov = Movimiento(stock_por_deposito=spd, tipo=tipo, cantidad=cantidad, fecha=fecha, externo_id=externo_id, documento=documento)
        try: mov.save()
        except IntegrityError as e: raise DuplicateError("Movimiento duplicado por externo_id") from e
        return mov
