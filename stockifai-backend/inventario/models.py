from django.db import models




##class Deposito(models.Model):
##    taller=models.ForeignKey('user.Taller', on_delete=models.PROTECT, related_name='depositos')
##    nombre=models.CharField(max_length=120)
##    class Meta: unique_together=[('taller','nombre')]
##    def __str__(self): return f"{self.taller_id} - {self.nombre}"


class Deposito(models.Model):
    taller = models.ForeignKey('user.Taller', on_delete=models.PROTECT, related_name='depositos')
    nombre = models.CharField(max_length=120)

    class Meta:
        unique_together = [('taller', 'nombre')]

    def __str__(self):
        # Muestra el nombre del taller y el nombre del depósito
        return f"{self.taller} - {self.nombre}"




class StockPorDeposito(models.Model):
    repuesto_taller = models.ForeignKey(
        'catalogo.RepuestoTaller',
        on_delete=models.PROTECT,
        related_name='stocks'
    )
    deposito = models.ForeignKey(
        'Deposito',
        on_delete=models.PROTECT,
        related_name='stocks'
    )
    cantidad = models.IntegerField(default=0)
    ubicacion = models.CharField(max_length=120, null=True, blank=True)
    notas = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = [('repuesto_taller', 'deposito')]

    def __str__(self):
        return f"RT:{self.repuesto_taller_id} DEP:{self.deposito_id} = {self.cantidad}"


class Ingreso(models.Model):
    id_ingreso = models.AutoField(primary_key=True)
    id_stock_por_deposito = models.ForeignKey(StockPorDeposito, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    fecha_ingreso = models.DateField()

    def __str__(self):
        return f"Ingreso de {self.cantidad} - {self.fecha_ingreso}"



class Movimiento(models.Model):
    TIPO=(('INGRESO','INGRESO'),('EGRESO','EGRESO'),('AJUSTE+','AJUSTE+'),('AJUSTE-','AJUSTE-'),('INICIAL+','INICIAL+'),('INICIAL-','INICIAL-'))
    stock_por_deposito=models.ForeignKey(StockPorDeposito, on_delete=models.PROTECT, related_name='movimientos')
    tipo=models.CharField(max_length=10, choices=TIPO); cantidad=models.IntegerField(); fecha=models.DateTimeField()
    documento=models.CharField(max_length=120, null=True, blank=True)
    externo_id=models.CharField(max_length=200, null=True, blank=True, db_index=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['stock_por_deposito','externo_id'],name='uq_mov_extid_por_stock',condition=~models.Q(externo_id=None))]
    def __str__(self): return f"{self.tipo} {self.cantidad} @ SPD {self.stock_por_deposito_id}"
