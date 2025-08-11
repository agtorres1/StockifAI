# inventario/repositories/categoria_repo.py
from catalogo.models import Categoria
from .base import NotFoundError

class CategoriaRepo:
    def get(self, pk: int) -> Categoria:
        try:
            return Categoria.objects.get(pk=pk)
        except Categoria.DoesNotExist:
            raise NotFoundError("Categoría no encontrada")

    def get_by_nombre(self, nombre: str) -> Categoria:
        try:
            return Categoria.objects.get(nombre__iexact=nombre)
        except Categoria.DoesNotExist:
            raise NotFoundError("Categoría no encontrada")

    def get_or_create(self, nombre: str):
        obj, _ = Categoria.objects.get_or_create(nombre__iexact=nombre, defaults={"nombre": nombre})
        # si tu get_or_create con __iexact no te gusta, reemplazá por
        #   match = Categoria.objects.filter(nombre__iexact=nombre).first()
        #   return match or Categoria.objects.create(nombre=nombre)
        class R: pass
        r = R(); r.obj = obj
        return r
