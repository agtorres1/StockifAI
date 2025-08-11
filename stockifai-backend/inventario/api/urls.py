from django.urls import path
from .views import ImportarMovimientosView, ImportarStockView, ImportarCatalogoView

urlpatterns = [ path('importaciones/movimientos', ImportarMovimientosView.as_view(), name='importar-movimientos'),
                path("importaciones/stock", ImportarStockView.as_view(), name="importar-stock"),
                path("importaciones/catalogo", ImportarCatalogoView.as_view(), name="importar-catalogo")

                ]


