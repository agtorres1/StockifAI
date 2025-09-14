from django.urls import path

from .categorias import CategoriasListView
from .marcas import MarcasListView
from .movimientos import MovimientosListView
from .repuestos import RepuestosListView
from .views import ImportarMovimientosView, ImportarStockView, ImportarCatalogoView, DepositosPorTallerView, \
    MovimientosEgresoTestView

urlpatterns = [
    path('importaciones/movimientos', ImportarMovimientosView.as_view(), name='importar-movimientos'),
    path("importaciones/stock", ImportarStockView.as_view(), name="importar-stock"),
    path("importaciones/catalogo", ImportarCatalogoView.as_view(), name="importar-catalogo"),
    path("talleres/<int:taller_id>/depositos", DepositosPorTallerView.as_view(), name="depositos-por-taller"),
    path("talleres/<int:taller_id>/movimientos", MovimientosListView.as_view(), name="movimientos-list"),
    path("marcas", MarcasListView.as_view(), name="marcas"),
    path("categorias", CategoriasListView.as_view(), name="categorias-list"),
    path("repuestos", RepuestosListView.as_view(), name="repuestos"),
]


