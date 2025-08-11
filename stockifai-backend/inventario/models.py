from django.db import models
class Deposito(models.Model):
    taller=models.ForeignKey('catalogo.Taller', on_delete=models.PROTECT, related_name='depositos')
    nombre=models.CharField(max_length=120)
    class Meta: unique_together=[('taller','nombre')]
    def __str__(self): return f"{self.taller_id} - {self.nombre}"
class RepuestoTaller(models.Model):
    repuesto=models.ForeignKey('catalogo.Repuesto', on_delete=models.PROTECT)
    taller=models.ForeignKey('catalogo.Taller', on_delete=models.PROTECT)
    precio=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    costo=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    original=models.BooleanField(default=True)
    class Meta: unique_together=[('repuesto','taller')]
    def __str__(self): return f"{self.repuesto_id}-{self.taller_id}"
class StockPorDeposito(models.Model):
    repuesto_taller=models.ForeignKey(RepuestoTaller, on_delete=models.PROTECT, related_name='stocks')
    deposito=models.ForeignKey(Deposito, on_delete=models.PROTECT, related_name='stocks')
    cantidad=models.IntegerField(default=0); cantidad_minima=models.IntegerField(default=0)
    class Meta: unique_together=[('repuesto_taller','deposito')]
    def __str__(self): return f"RT:{self.repuesto_taller_id} DEP:{self.deposito_id} = {self.cantidad}"
class Movimiento(models.Model):
    TIPO=(('INGRESO','INGRESO'),('EGRESO','EGRESO'),('AJUSTE+','AJUSTE+'),('AJUSTE-','AJUSTE-'))
    stock_por_deposito=models.ForeignKey(StockPorDeposito, on_delete=models.PROTECT, related_name='movimientos')
    tipo=models.CharField(max_length=10, choices=TIPO); cantidad=models.IntegerField(); fecha=models.DateTimeField()
    documento=models.CharField(max_length=120, null=True, blank=True)
    externo_id=models.CharField(max_length=200, null=True, blank=True, db_index=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['stock_por_deposito','externo_id'],name='uq_mov_extid_por_stock',condition=~models.Q(externo_id=None))]
    def __str__(self): return f"{self.tipo} {self.cantidad} @ SPD {self.stock_por_deposito_id}"
