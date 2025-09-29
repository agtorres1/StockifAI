
from django.db import models

class Direccion(models.Model):
    id_direccion = models.AutoField(primary_key=True)
    calle = models.CharField(max_length=100, null=True, blank=True)
    numero = models.CharField(max_length=10, null=True, blank=True)
    codigo_postal = models.CharField(max_length=10, null=True, blank=True)
    id_barrio = models.ForeignKey(Barrio, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.calle} {self.numero}, {self.id_barrio.nombre}"