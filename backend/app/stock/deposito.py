from django.db import models


class Deposito(models.Model):
    id_deposito = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_taller = models.ForeignKey(Taller, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre
