# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("callback/", views.callback_view, name="callback"),
]
