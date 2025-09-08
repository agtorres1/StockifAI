from .base import RepoResult
from catalogo.models import RepuestoTaller
from catalogo.models import Repuesto
from user.models import Taller
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