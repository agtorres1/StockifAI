# inventario/repositories/marca_repo.py
from catalogo.models import Marca
from .base import NotFoundError

class MarcaRepo:
    def get(self, pk: int) -> Marca:
        try:
            return Marca.objects.get(pk=pk)
        except Marca.DoesNotExist:
            raise NotFoundError("Marca no encontrada")

    def get_by_nombre(self, nombre: str) -> Marca:
        try:
            return Marca.objects.get(nombre__iexact=nombre)
        except Marca.DoesNotExist:
            raise NotFoundError("Marca no encontrada")

    def get_or_create(self, nombre: str):
        obj, _ = Marca.objects.get_or_create(nombre__iexact=nombre, defaults={"nombre": nombre})
        class R: pass
        r = R(); r.obj = obj
        return r
