from django.db import models

class Movimiento(models.Model):
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('SALIDA', 'Salida'),
        ('AJUSTE', 'Ajuste'),
    ]

    id_movimiento = models.AutoField(primary_key=True)
    id_stock_por_deposito = models.ForeignKey(StockPorDeposito, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.IntegerField()
    fecha = models.DateField()

    def __str__(self):
        return f"{self.tipo} - {self.cantidad} ({self.fecha})"