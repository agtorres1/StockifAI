from django.contrib import admin
from .models import Deposito, RepuestoTaller, StockPorDeposito, Movimiento
admin.site.register(Deposito); admin.site.register(RepuestoTaller); admin.site.register(StockPorDeposito); admin.site.register(Movimiento)
