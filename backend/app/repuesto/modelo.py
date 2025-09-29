from django.db import models

class Modelo(models.Model):
    id_modelo = models.AutoField(primary_key=True)
    id_marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    fecha_creacion = models.DateField()

    def __str__(self):
        return f"{self.nombre} ({self.id_marca.nombre})"