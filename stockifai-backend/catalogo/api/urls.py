from django.urls import path

from .categorias import CategoriasListView
from .marcas import MarcasListView
from .repuestos import RepuestosListView

urlpatterns = [
    path("marcas", MarcasListView.as_view(), name="marcas"),
    path("categorias", CategoriasListView.as_view(), name="categorias-list"),
    path("repuestos", RepuestosListView.as_view(), name="repuestos"),
]


