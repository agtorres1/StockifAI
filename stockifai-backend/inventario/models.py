from django.db import models
from user.api.models.models import Taller, Grupo
from django.utils import timezone
from datetime import datetime, timedelta


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


class ObjetivoKPI(models.Model):
    """Objetivos de KPIs por taller o grupo"""

    taller = models.OneToOneField(
        Taller,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='objetivo_kpi'
    )
    grupo = models.OneToOneField(
        Grupo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='objetivo_kpi'
    )

    # ===== OBJETIVOS (todos configurables) =====
    tasa_rotacion_objetivo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.5,
        help_text="Objetivo de tasa de rotación trimestral"
    )

    dias_en_mano_objetivo = models.IntegerField(
        default=60,
        help_text="Objetivo de días en mano"
    )

    dead_stock_objetivo = models.DecimalField(  # ← NUEVO
        max_digits=5,
        decimal_places=2,
        default=10.0,
        help_text="Porcentaje máximo aceptable de dead stock"
    )

    dias_dead_stock = models.IntegerField(
        default=730,
        help_text="Días sin movimiento para considerar dead stock (2 años)"
    )

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.taller:
            return f"Objetivos KPI - {self.taller.nombre}"
        if self.grupo:
            return f"Objetivos KPI - {self.grupo.nombre}"
        return f"Objetivos KPI #{self.id}"

    class Meta:
        verbose_name = "Objetivo KPI"
        verbose_name_plural = "Objetivos KPI"