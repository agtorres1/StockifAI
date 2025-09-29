
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from auth0_backend.jwt_utils import decode_jwt
from user.api.models.models import User, Direccion
from django.contrib.auth import login
import jwt

# user/views.py

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt


# user/views.py
from django.shortcuts import render, redirect
from django.conf import settings


from ...forms import RegisterForm

from django.contrib.auth import authenticate, login

from rest_framework import viewsets


import json
import traceback
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from ...auth0_utils import get_mgmt_token  # tu función para el token de Auth0
from user.api.serializers.user_serializer import UserSerializer


@csrf_exempt
def login_view(request):
    print("===== DEBUG login_api =====")

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    # Parsear JSON
    try:
        data = json.loads(request.body)
        print("===== DEBUG: JSON recibido =====", data)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    email = data.get("email", "")
    password = data.get("password", "")
    print(f"===== DEBUG: email={email}, password={'*' * len(password)} =====")

    # Autenticar usuario
    try:
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            print("✅ Usuario autenticado correctamente:", user.id)
            return JsonResponse({"message": "Login exitoso", "user_id": user.id})
        else:
            print("❌ Error de autenticación: usuario o contraseña incorrectos")
            return JsonResponse({"error": "Usuario o contraseña incorrectos"}, status=401)
    except Exception as e:
        tb = traceback.format_exc()
        print("❌ ERROR LOGIN:", tb)
        return JsonResponse({"error": str(e), "traceback": tb}, status=500)

def logout(request):
    request.session.flush()
    return redirect(f"https://{settings.AUTH0_DOMAIN}/v2/logout?returnTo=http://localhost:8000/")

def callback(request):
    code = request.GET.get('code')

    # Intercambiar code por id_token
    token_info = requests.post(
        f"https://{settings.AUTH0_DOMAIN}/oauth/token",
        data={
            'grant_type': 'authorization_code',
            'client_id': settings.AUTH0_CLIENT_ID,
            'client_secret': settings.AUTH0_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.AUTH0_CALLBACK_URL
        }
    ).json()

    id_token = token_info.get('id_token')

    # Decodificar id_token SIN verificar firma
    user_info = jwt.decode(id_token, options={"verify_signature": False})

    # Guardar info del usuario en sesión
    request.session['user'] = user_info

    return redirect('/dashboard/')



@csrf_exempt
def register_api(request):
    print("===== DEBUG register_api =====")

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)


    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)


    form = RegisterForm(data)
    if not form.is_valid():
        print("❌ Errores del formulario:", form.errors)
        return JsonResponse({"error": form.errors}, status=400)


    nombre = form.cleaned_data.get("nombre", "")
    apellido = form.cleaned_data.get("apellido", "")
    email = form.cleaned_data["email"]
    password = form.cleaned_data["password"]

    calle = form.cleaned_data.get("calle", "")
    ciudad = form.cleaned_data.get("ciudad", "")
    codigo_postal = form.cleaned_data.get("codigo_postal", "")
    telefono = form.cleaned_data.get("telefono", "")

    print("===== DEBUG: Datos recibidos correctamente =====")


    try:
        direccion_obj = Direccion.objects.create(
            calle=calle,
            ciudad=ciudad,
            codigo_postal=codigo_postal,
        )
        print("✅ Dirección creada:", direccion_obj)
    except Exception as e:
        tb = traceback.format_exc()
        print("❌ ERROR DIRECCION:", tb)
        return JsonResponse({"error": f"Error al crear dirección: {str(e)}", "traceback": tb}, status=500)


    try:
        mgmt_token = get_mgmt_token()
        url = f"https://{settings.AUTH0_DOMAIN}/api/v2/users"
        headers = {
            "Authorization": f"Bearer {mgmt_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "password": password,
            "connection": "Username-Password-Authentication",
            "given_name": nombre,
            "family_name": apellido,
            "user_metadata": {
                "direccion": f"{calle}, {ciudad}",
                "telefono": telefono
            }
        }

        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        auth0_user = r.json()
        print("✅ Usuario creado en Auth0:", auth0_user.get("user_id"))
    except requests.exceptions.HTTPError as e:
        tb = traceback.format_exc()
        print("❌ ERROR AUTH0:", tb)
        return JsonResponse({"error": str(e), "traceback": tb, "response": r.text}, status=r.status_code)
    except Exception as e:
        tb = traceback.format_exc()
        print("❌ ERROR AUTH0:", tb)
        return JsonResponse({"error": str(e), "traceback": tb}, status=500)


    try:
        local_user = User.objects.create_user(
            username=email,
            email=email,
            first_name=nombre,
            last_name=apellido,
            direccion=direccion_obj,
            telefono=telefono,
            password=password
        )
        print("✅ Usuario local creado:", local_user.id)
    except Exception as e:
        tb = traceback.format_exc()
        print("❌ ERROR LOCAL DB:", tb)
        return JsonResponse({"error": f"Error al crear usuario local: {str(e)}", "traceback": tb}, status=500)

    return JsonResponse({
        "message": "✅ Usuario creado correctamente",
        "auth0_id": auth0_user.get("user_id"),
        "local_id": local_user.id
    })

# user/views.py (continuación)
def get_mgmt_token():
    url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    payload = {
        "client_id": settings.AUTH0_MGMT_CLIENT_ID,
        "client_secret": settings.AUTH0_MGMT_CLIENT_SECRET,
        "audience": f"https://{settings.AUTH0_DOMAIN}/api/v2/",
        "grant_type": "client_credentials"
    }
    r = requests.post(url, json=payload)
    return r.json()["access_token"]



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer










