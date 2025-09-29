from django.db import models

class ModeloRepuesto(models.Model):
    id_modelo_repuesto = models.AutoField(primary_key=True)
    id_modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE)
    id_repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id_modelo.nombre} - {self.id_repuesto.descripcion}"