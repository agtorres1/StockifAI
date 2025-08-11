from .base import NotFoundError
from catalogo.models import Taller
class TallerRepo:
    def get(self, taller_id: int) -> Taller:
        try: return Taller.objects.get(pk=taller_id)
        except Taller.DoesNotExist: raise NotFoundError(f"Taller {taller_id} no existe")
