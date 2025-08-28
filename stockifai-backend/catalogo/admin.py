from django.contrib import admin

from .models import Marca, Categoria, Repuesto, RepuestoTaller
admin.site.register(Marca); admin.site.register(Categoria); admin.site.register(Repuesto); admin.site.register(RepuestoTaller)
