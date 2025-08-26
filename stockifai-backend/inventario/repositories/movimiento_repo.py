from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta
from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone

from .base import DuplicateError
from inventario.models import Movimiento, StockPorDeposito
class MovimientoRepo:
    def crear_unico(self, spd: StockPorDeposito, *, tipo: str, cantidad: int, fecha, externo_id: str | None, documento: str | None=None) -> Movimiento:
        mov = Movimiento(stock_por_deposito=spd, tipo=tipo, cantidad=cantidad, fecha=fecha, externo_id=externo_id, documento=documento)
        try: mov.save()
        except IntegrityError as e: raise DuplicateError("Movimiento duplicado por externo_id") from e
        return mov

    def get_egresos_ultimos_5_anios(self, taller_id: int):
        """
        Devuelve movimientos de EGRESO para el taller indicado, de los últimos 5 años.
        """

        cant_anios = 5

        hasta_date = timezone.now()
        desde_date = (hasta_date - relativedelta(years=cant_anios)).date()

        desde_dt = datetime.combine(desde_date, time.min)
        hasta_dt = datetime.combine(hasta_date, time.max)

        query_set = (
            Movimiento.objects
            .filter(
                stock_por_deposito__repuesto_taller__taller_id=taller_id,
                tipo="EGRESO",
                fecha__gte=desde_dt,
                fecha__lt=hasta_dt,
            )
            .annotate(
                numero_pieza=F("stock_por_deposito__repuesto_taller__repuesto__numero_pieza"),
                descripcion=F("stock_por_deposito__repuesto_taller__repuesto__descripcion"),
            )
            .values("id", "numero_pieza", "descripcion", "fecha", "cantidad")
            .order_by("fecha")
        )
        return query_set

