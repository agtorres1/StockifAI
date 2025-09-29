from django.db import models

class Ingreso(models.Model):
    id_ingreso = models.AutoField(primary_key=True)
    id_stock_por_deposito = models.ForeignKey(StockPorDeposito, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    fecha_ingreso = models.DateField()

    def __str__(self):
        return f"Ingreso de {self.cantidad} - {self.fecha_ingreso}"