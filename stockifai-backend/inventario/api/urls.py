from django.urls import path, include

from .movimientos import MovimientosListView
from .views import ImportarMovimientosView, ImportarStockView, ImportarCatalogoView, DepositosPorTallerView, \
    ConsultarStockView, EjecutarForecastPorTallerView, EjecutarForecastView
from rest_framework.routers import DefaultRouter
#from inventario.api.compras import ComprasViewSet
from .views import KPIsViewSet


router = DefaultRouter()
#router.register(r'compras', ComprasViewSet, basename='compras')
router.register(r'kpis', KPIsViewSet, basename='kpis')

urlpatterns = [

    path('', include(router.urls)),
    
    path('importaciones/movimientos', ImportarMovimientosView.as_view(), name='importar-movimientos'),
    path("importaciones/stock", ImportarStockView.as_view(), name="importar-stock"),
    path("importaciones/catalogo", ImportarCatalogoView.as_view(), name="importar-catalogo"),
    path("talleres/<int:taller_id>/depositos", DepositosPorTallerView.as_view(), name="depositos-por-taller"),
    path("talleres/<int:taller_id>/movimientos", MovimientosListView.as_view(), name="movimientos-list"),
    path("talleres/<int:taller_id>/stock", ConsultarStockView.as_view(), name="consultar-stock"),
    path("talleres/<int:taller_id>/forecast/run", EjecutarForecastPorTallerView.as_view(), name="forecast-run-taller"),
    path("talleres/forecast/run", EjecutarForecastView.as_view(), name="forecast-run"),

]


