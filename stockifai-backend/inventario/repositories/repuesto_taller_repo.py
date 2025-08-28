from .base import RepoResult
from catalogo.models import RepuestoTaller
from catalogo.models import Repuesto
from user.models import Taller
class RepuestoTallerRepo:
    def get_or_create(self, repuesto: Repuesto, taller: Taller) -> RepoResult:
        obj, created = RepuestoTaller.objects.get_or_create(repuesto=repuesto, taller=taller)
        return RepoResult(obj=obj, created=created)
