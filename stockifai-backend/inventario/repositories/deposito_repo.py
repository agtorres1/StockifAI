from .base import RepoResult
from inventario.models import Deposito
from user.models import Taller
class DepositoRepo:
    def get_or_create(self, taller: Taller, nombre: str) -> RepoResult:
        obj, created = Deposito.objects.get_or_create(taller=taller, nombre=nombre.strip())
        return RepoResult(obj=obj, created=created)
