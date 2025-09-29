from .base import RepoResult
from catalogo.models import RepuestoTaller
from catalogo.models import Repuesto
from user.api.models.models import Taller

class RepuestoTallerRepo:
    def get_or_create(self, repuesto: Repuesto, taller: Taller) -> RepoResult:
        obj, created = RepuestoTaller.objects.get_or_create(repuesto=repuesto, taller=taller)
        return RepoResult(obj=obj, created=created)

    def set_predicciones(self, repuesto: Repuesto, taller: Taller, predicciones: dict) -> RepuestoTaller:
        """

            predicciones (dict): diccionario con las predicciones, por ejemplo:
                {
                    'pred_1': 10,
                    'pred_2': 12,
                    'pred_3': 15,
                    'pred_4': 9
                }
        Devuelve:
            RepuestoTaller: el objeto actualizado.
        """
        repo_result = self.get_or_create(repuesto, taller) #ver si hacer una sola funcion de get
        obj = repo_result.obj

        # Asignar valores si existen en el diccionario
        for semana in range(1, 5):
            key = f'pred_{semana}'
            if key in predicciones:
                setattr(obj, key, predicciones[key])

        obj.save()
        return obj

    def list_by_taller_and_repuestos(self, taller: Taller, repuesto_ids: list[int]) -> list[RepuestoTaller]:
        """
        Devuelve todos los RepuestoTaller de un taller para una lista de repuesto_ids.
        """
        if not repuesto_ids:
            return []
        return list(
            RepuestoTaller.objects.filter(taller=taller, repuesto_id__in=repuesto_ids)
            .only("id_repuesto_taller", "repuesto_id", "taller_id")
        )