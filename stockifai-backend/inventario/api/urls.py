from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .movimientos import MovimientosListView
from .views import (
    ImportarMovimientosView,
    ImportarStockView,
    ImportarCatalogoView,
    DepositosPorTallerView,
    ConsultarStockView,
    LocalizarRepuestoView,
    EjecutarForecastPorTallerView,
    EjecutarForecastView,
    DetalleForecastingView,
    ConsultarForecastingListView,
    AlertsListView,
    DismissAlertView,
    MarkAsSeenAlertView,
    AlertsForRepuestoView,
    MarkAllAsSeenView,
    ExportarUrgentesView, SaludInventarioPorCategoriaView, ExportarSaludInventarioView,
    ExportarUrgentesView,
    SaludInventarioPorCategoriaView,
    KPIsViewSet,
    DepositosPorGrupoView,
    GrupoDetailView,
)

router = DefaultRouter()
router.register(r'kpis', KPIsViewSet, basename='kpis')

urlpatterns = [
    path('', include(router.urls)),

    path('importaciones/movimientos', ImportarMovimientosView.as_view(), name='importar-movimientos'),
    path("importaciones/stock", ImportarStockView.as_view(), name="importar-stock"),
    path("importaciones/catalogo", ImportarCatalogoView.as_view(), name="importar-catalogo"),
    path("talleres/<int:taller_id>/depositos", DepositosPorTallerView.as_view(), name="depositos-por-taller"),
    path("grupos/<int:grupo_id>/depositos", DepositosPorGrupoView.as_view(), name="depositos-por-grupo"),
    path("grupos/<int:grupo_id>/", GrupoDetailView.as_view(), name="grupo-detail"),

    path("talleres/<int:taller_id>/movimientos", MovimientosListView.as_view(), name="movimientos-list"),
    path("talleres/<int:taller_id>/stock", ConsultarStockView.as_view(), name="consultar-stock"),
    path("talleres/<int:taller_id>/localizador", LocalizarRepuestoView.as_view(), name="localizar-repuesto"),
    path("talleres/<int:taller_id>/forecast/run", EjecutarForecastPorTallerView.as_view(), name="forecast-run-taller"),
    path("talleres/forecast/run", EjecutarForecastView.as_view(), name="forecast-run"),
    path("talleres/<int:taller_id>/forecasting", ConsultarForecastingListView.as_view(), name="forecasting-list"),
    path("talleres/<int:taller_id>/repuestos/<int:repuesto_taller_id>/forecasting", DetalleForecastingView.as_view(),
         name="detalle-forecasting"),
    path("talleres/<int:taller_id>/alertas/", AlertsListView.as_view(), name="alertas-list"),
    path("alertas/<int:alerta_id>/dismiss/", DismissAlertView.as_view(), name="alertas-list"),
    path("alertas/<int:alerta_id>/mark-as-seen/", MarkAsSeenAlertView.as_view(), name="marcar-vista-alerta"),
    path("talleres/<int:taller_id>/alertas/mark-all-as-seen/", MarkAllAsSeenView.as_view(),
         name="marcar-todas-vista-alerta"),
    path("talleres/<int:taller_id>/repuestos/<int:repuesto_taller_id>/alertas/", AlertsForRepuestoView.as_view(),
         name="alertas-por-repuesto"),
    path("talleres/<int:taller_id>/exportar-urgentes/", ExportarUrgentesView.as_view(), name="exportar-urgentes"),
    path("talleres/<int:taller_id>/salud-por-categoria/", SaludInventarioPorCategoriaView.as_view(), name="salud-por-categoria"),
    path("talleres/<int:taller_id>/salud-inventario/exportar/", ExportarSaludInventarioView.as_view(), name="exportar-salud-inventario"),
    path("talleres/<int:taller_id>/salud-por-categoria/", SaludInventarioPorCategoriaView.as_view(),
         name="salud-por-categoria"),
]
