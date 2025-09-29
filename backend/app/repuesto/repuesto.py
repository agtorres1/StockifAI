from django.db import models

class Repuesto(models.Model):
    id_repuesto = models.AutoField(primary_key=True)
    id_marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField()
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.descripcion} - {self.id_marca.nombre}"