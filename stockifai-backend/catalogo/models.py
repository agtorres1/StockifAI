
from django.db import models

class Marca(models.Model): ####
    nombre=models.CharField(max_length=120, unique=True)
    def __str__(self): return self.nombre

class Categoria(models.Model): ####
    nombre=models.CharField(max_length=120, unique=True); descripcion=models.TextField(blank=True)
    def __str__(self): return self.nombre



class Modelo(models.Model):
    id_modelo = models.AutoField(primary_key=True)
    id_marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    fecha_creacion = models.DateField()

    def __str__(self):
        return f"{self.nombre} ({self.id_marca.nombre})"

class Repuesto(models.Model): ####
    numero_pieza=models.CharField(max_length=120, unique=True, db_index=True)
    descripcion=models.CharField(max_length=255, blank=True)
    marca=models.ForeignKey(Marca, on_delete=models.PROTECT, null=True, blank=True)
    categoria=models.ForeignKey(Categoria, on_delete=models.PROTECT, null=True, blank=True)
    estado=models.CharField(max_length=50, default='activo')
    lead_time = models.IntegerField(null=True, blank=True)



    def __str__(self): return f"{self.numero_pieza} - {self.descripcion or ''}"



class ModeloRepuesto(models.Model): #####
    id_modelo_repuesto = models.AutoField(primary_key=True)
    id_modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE)
    id_repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id_modelo.nombre} - {self.id_repuesto.descripcion}"



class RepuestoTaller(models.Model):
    id_repuesto_taller = models.AutoField(primary_key=True)
    repuesto = models.ForeignKey('catalogo.Repuesto', on_delete=models.PROTECT)
    taller = models.ForeignKey('user.Taller', on_delete=models.PROTECT)
    frecuencia = models.CharField(max_length=100, null=True, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    costo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    original = models.BooleanField(default=True)
    pred_1 = models.IntegerField(null=True, blank=True)
    pred_2 = models.IntegerField(null=True, blank=True)
    pred_3 = models.IntegerField(null=True, blank=True)
    pred_4 = models.IntegerField(null=True, blank=True)



    class Meta:
        unique_together = [('repuesto', 'taller')]

    def __str__(self):
        return f"{self.repuesto.descripcion} - {self.taller.nombre}"









