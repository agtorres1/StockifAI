from django.db.models import F
from .base import RepoResult, StockInsufficientError
from inventario.models import StockPorDeposito, Deposito
from catalogo.models import RepuestoTaller

class StockRepo:
    def get_or_create(self, rt: RepuestoTaller, deposito: Deposito) -> RepoResult:
        obj, created = StockPorDeposito.objects.get_or_create(repuesto_taller=rt, deposito=deposito)
        return RepoResult(obj=obj, created=created)
    def agregar(self, spd: StockPorDeposito, cantidad: int) -> None:
        StockPorDeposito.objects.filter(pk=spd.pk).update(cantidad=F('cantidad') + cantidad)
    def egresar(self, spd: StockPorDeposito, cantidad: int, permitir_negativo: bool=False) -> None:
        spd.refresh_from_db(fields=['cantidad']); disponible = spd.cantidad or 0
        if not permitir_negativo and disponible - cantidad < 0:
            raise StockInsufficientError(f"Stock insuficiente: {disponible} < {cantidad}")
        StockPorDeposito.objects.filter(pk=spd.pk).update(cantidad=F('cantidad') - cantidad)

    def list_by_rt_ids_and_depositos(self, rt_ids: list[int], deposito_ids: list[int]) -> list[StockPorDeposito]:
        """
        Devuelve todos los StockPorDeposito cuyo repuesto_taller_id ∈ rt_ids
        y deposito_id ∈ deposito_ids (una sola query).
        """
        if not rt_ids or not deposito_ids:
            return []
        return list(
            StockPorDeposito.objects.filter(
                repuesto_taller_id__in=rt_ids,
                deposito_id__in=deposito_ids
            ).only(
                "id", "repuesto_taller_id", "deposito_id", "cantidad", "cantidad_minima"
            )
        )