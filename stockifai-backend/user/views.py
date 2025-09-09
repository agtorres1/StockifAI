
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

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
    return JsonResponse({"token": token})
