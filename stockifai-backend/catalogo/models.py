from django.db import models
class Taller(models.Model):
    nombre=models.CharField(max_length=120); direccion=models.CharField(max_length=255, blank=True)
    telefono=models.CharField(max_length=50, blank=True); email=models.EmailField(blank=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nombre
class Marca(models.Model):
    nombre=models.CharField(max_length=120, unique=True)
    def __str__(self): return self.nombre
class Categoria(models.Model):
    nombre=models.CharField(max_length=120, unique=True); descripcion=models.TextField(blank=True)
    def __str__(self): return self.nombre
class Repuesto(models.Model):
    numero_pieza=models.CharField(max_length=120, unique=True, db_index=True)
    descripcion=models.CharField(max_length=255, blank=True)
    marca=models.ForeignKey(Marca, on_delete=models.PROTECT, null=True, blank=True)
    categoria=models.ForeignKey(Categoria, on_delete=models.PROTECT, null=True, blank=True)
    estado=models.CharField(max_length=50, default='activo')
    def __str__(self): return f"{self.numero_pieza} - {self.descripcion or ''}"
