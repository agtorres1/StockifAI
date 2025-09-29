from django.db import models

class RepuestoTaller(models.Model):
    id_repuesto_taller = models.AutoField(primary_key=True)
    id_repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE)
    id_taller = models.ForeignKey(Taller, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    original = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.id_repuesto.descripcion} - {self.id_taller.nombre}"