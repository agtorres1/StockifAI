
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from auth0_backend.jwt_utils import decode_jwt
from user.models import User
from django.contrib.auth import login

def login_view(request):
    auth0_domain = settings.AUTH0_DOMAIN
    client_id = settings.AUTH0_CLIENT_ID
    redirect_uri = "http://127.0.0.1:8000/user/callback/"
    audience = settings.AUTH0_AUDIENCE  # ⚡ reemplazar API_IDENTIFIER


    return redirect(
        f"https://{auth0_domain}/authorize?"
        f"response_type=token&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=openid profile email&"
        f"audience={audience}"
    )

def callback_view(request):
    token = request.GET.get("access_token")
    if not token:
        return JsonResponse({"error": "Token no recibido"}, status=400)

    payload = decode_jwt(token)
    email = payload.get("email")
    name = payload.get("name")

    # Crear o actualizar usuario en la base de datos
    user, created = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": name})
    if not created:
        user.email = email
        user.first_name = name
        user.save()

    login(request, user)
    return JsonResponse({"ok": True, "user": {"username": user.username, "email": user.email}})
