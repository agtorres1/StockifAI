# inventario/repositories/repuesto_repo.py
from catalogo.models import Repuesto
from .base import NotFoundError

class RepuestoRepo:
    def get_by_numero(self, numero_pieza: str) -> Repuesto:
        try:
            return Repuesto.objects.get(numero_pieza__iexact=numero_pieza)
        except Repuesto.DoesNotExist:
            raise NotFoundError("Repuesto no encontrado")

    def create(self, *, numero_pieza: str, descripcion: str,
               estado: str = "ACTIVO", categoria=None, marca=None) -> Repuesto:
        obj = Repuesto(
            numero_pieza=numero_pieza,
            descripcion=descripcion,
            estado=estado,
        )
        if categoria is not None:
            obj.categoria = categoria
        if marca is not None:
            obj.marca = marca
        obj.save()
        return obj

    def update_fields(self, repuesto: Repuesto, **fields) -> Repuesto:
        changed = False
        for k, v in fields.items():
            if hasattr(repuesto, k) and getattr(repuesto, k) != v and v is not None:
                setattr(repuesto, k, v)
                changed = True
        if changed:
            repuesto.save(update_fields=[k for k, v in fields.items() if v is not None])
        return repuesto

    # opcional, por si querés usar un único método en el servicio
    def upsert(self, *, numero_pieza: str, descripcion: str,
               estado: str = "ACTIVO", categoria=None, marca=None) -> tuple[Repuesto, bool]:
        """Devuelve (obj, created)"""
        try:
            obj = self.get_by_numero(numero_pieza)
            self.update_fields(obj,
                descripcion=descripcion,
                estado=estado,
                categoria=categoria,
                marca=marca,
            )
            return obj, False
        except NotFoundError:
            return self.create(
                numero_pieza=numero_pieza,
                descripcion=descripcion,
                estado=estado,
                categoria=categoria,
                marca=marca,
            ), True

    def list_by_numeros(self, numeros: list[str]):
        """
        Devuelve todos los repuestos cuyos numeros estén en la lista.
        """
        if not numeros:
            return []
        return list(
            Repuesto.objects.filter(numero_pieza__in=numeros)
            .only("id", "numero_pieza", "descripcion", "estado", "categoria_id", "marca_id")
        )
