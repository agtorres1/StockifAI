from django.db import models


class Taller(models.Model):
    id_taller = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    fecha_creacion = models.DateField()
    grupos = models.ManyToManyField(Grupo, through='GrupoTaller')

    def __str__(self):
        return self.nombre