from django.urls import path

from .movimientos import MovimientosListView
from .views import ImportarMovimientosView, ImportarStockView, ImportarCatalogoView, DepositosPorTallerView

urlpatterns = [
    path('importaciones/movimientos', ImportarMovimientosView.as_view(), name='importar-movimientos'),
    path("importaciones/stock", ImportarStockView.as_view(), name="importar-stock"),
    path("importaciones/catalogo", ImportarCatalogoView.as_view(), name="importar-catalogo"),

    path("talleres/<int:taller_id>/depositos", DepositosPorTallerView.as_view(), name="depositos-por-taller"),
    path("talleres/<int:taller_id>/movimientos", MovimientosListView.as_view(), name="movimientos-list"),
]


