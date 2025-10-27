# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from user.api.views.views_user import UserViewSet
from user.api.views.talleres import TallerViewSet, TallerView
from user.api.views.grupo_view import GrupoViewSet, GrupoTallerViewSet
from user.api.views.views_user import login_view, logout_view, callback, register_api, check_session, force_login

router = DefaultRouter()
router.register(r"talleres", TallerViewSet, basename="taller")
router.register(r"usuarios", UserViewSet, basename="usuario")
router.register(r"grupos", GrupoViewSet, basename="grupo")
router.register(r"grupo-taller", GrupoTallerViewSet, basename="grupo-taller")

urlpatterns = [
    # Rutas de autenticación (públicas)
    path("register/", register_api, name="register"),
    path("login/", login_view, name="login"),
    path("callback/", callback, name="callback"),
    path("logout/", logout_view, name="logout"),
    path("check-session/", check_session, name="check_session"),
    path('force-login/', force_login, name='force-login'),

    # Rutas adicionales
    path("taller-data/<int:taller_id>", TallerView.as_view(), name="taller-info"),

    # Rutas del router (protegidas automáticamente por el middleware)
    path("", include(router.urls)),
]