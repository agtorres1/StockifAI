from django.contrib import admin

from .models import Deposito, StockPorDeposito, Movimiento
admin.site.register(Deposito); admin.site.register(StockPorDeposito); admin.site.register(Movimiento)
