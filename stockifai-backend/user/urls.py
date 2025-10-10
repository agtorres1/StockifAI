# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from user.api.views.views_user import UserViewSet
from user.api.views.talleres import TallerViewSet
from user.api.views.grupo_view import GrupoViewSet
from user.api.views.grupo_view import GrupoTallerViewSet
from user.api.views.talleres import TallerView
from user.api.views.views_user import login_view, logout, callback, register_api


router = DefaultRouter()
router.register(r"talleres", TallerViewSet, basename="taller")
router.register(r"usuarios", UserViewSet, basename="usuario")  # 👈 acá agregás usuarios
router.register(r"grupos", GrupoViewSet, basename="grupo")
router.register(r"grupo-taller", GrupoTallerViewSet, basename="grupo-taller")

urlpatterns = [
    path("login/", login_view, name="login"),
    path('logout/', logout, name='logout'),
    path("callback/", callback, name="callback"),
    path("register/", register_api, name="register"),
    path("taller-data/<int:taller_id>", TallerView.as_view(), name="taller-info"),
    path("", include(router.urls)),
]
