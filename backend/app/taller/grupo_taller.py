from django.db import models


class GrupoTaller(models.Model):
    id_grupo_taller = models.AutoField(primary_key=True)
    id_grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    id_taller = models.ForeignKey(Taller, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id_grupo.nombre} - {self.id_taller.nombre}"