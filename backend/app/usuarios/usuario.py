
from django.db import models


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    contraseña = models.CharField(max_length=128)  # En Django normalmente se usa hashed
    fecha_creacion = models.DateField(auto_now_add=True)
    id_taller = models.ForeignKey(Taller, on_delete=models.SET_NULL, null=True, blank=True)
    id_grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True)
    id_rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.email})"