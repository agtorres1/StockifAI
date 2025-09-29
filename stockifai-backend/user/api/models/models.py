from django.db import models
from django.contrib.auth.models import AbstractUser

class Direccion(models.Model):
    id_direccion = models.AutoField(primary_key=True)
    calle = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    

    def __str__(self):
        return f"{self.calle}, {self.ciudad}"

class Taller(models.Model):
    nombre = models.CharField(max_length=120)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Grupo(models.Model):
    id_grupo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre

class GrupoTaller(models.Model):
    id_grupo_taller = models.AutoField(primary_key=True)
    id_grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    id_taller = models.ForeignKey(Taller, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id_grupo.nombre} - {self.id_taller.nombre}"

class User(AbstractUser):
    taller = models.ForeignKey(Taller, on_delete=models.SET_NULL, null=True, blank=True)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True)
    direccion = models.OneToOneField(Direccion, on_delete=models.SET_NULL, null=True, blank=True)

    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'custom_user'




