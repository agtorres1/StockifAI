from .base import RepoResult
from inventario.models import Deposito
from user.api.models.models import Taller



class DepositoRepo:
    def get_or_create(self, taller: Taller, nombre: str) -> RepoResult:
        obj, created = Deposito.objects.get_or_create(taller=taller, nombre=nombre.strip())
        return RepoResult(obj=obj, created=created)

    def list_by_nombres(self, taller, nombres: list[str]):
        """
        Devuelve todos los depósitos de un taller cuyos nombres estén en la lista.
        """
        if not nombres:
            return []
        return list(
            Deposito.objects.filter(taller=taller, nombre__in=nombres)
            .only("id", "nombre", "taller_id")
        )