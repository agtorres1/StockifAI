from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.contrib.auth import authenticate, login
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

import json
import traceback
import requests
import jwt

from auth0_backend.jwt_utils import decode_jwt
from user.api.models.models import User, Direccion, Grupo, Taller
from user.api.serializers.user_serializer import UserSerializer
from ...forms import RegisterForm
from ...auth0_utils import get_mgmt_token
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

import json
import traceback
import requests
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from ...auth0_utils import get_mgmt_token  # tu función para el token de Auth0
from user.api.serializers.user_serializer import UserSerializer
from user.api.models.models import Taller

@csrf_exempt
def login_view(request):
    # Redirigir al usuario a la página de login de Auth0
    auth0_url = (
        f"https://{settings.AUTH0_DOMAIN}/authorize?"
        f"response_type=code&"
        f"client_id={settings.AUTH0_CLIENT_ID}&"
        f"redirect_uri={settings.AUTH0_CALLBACK_URL}&"
        f"scope=openid profile email"
    )
    return redirect(auth0_url)


def callback(request):
    """Auth0 redirige aquí después del login"""
    code = request.GET.get('code')

    # Intercambiar code por tokens
    token_response = requests.post(
        f"https://{settings.AUTH0_DOMAIN}/oauth/token",
        data={
            'grant_type': 'authorization_code',
            'client_id': settings.AUTH0_CLIENT_ID,
            'client_secret': settings.AUTH0_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.AUTH0_CALLBACK_URL
        }
    ).json()

    id_token = token_response.get('id_token')
    access_token = token_response.get('access_token')

    # Decodificar id_token para obtener info del usuario
    user_info = jwt.decode(id_token, options={"verify_signature": False})

    # Buscar o crear usuario local
    email = user_info.get('email')
    try:
        local_user = User.objects.get(email=email)
    except User.DoesNotExist:
        local_user = User.objects.create(
            username=email,
            email=email,
            first_name=user_info.get('given_name', ''),
            last_name=user_info.get('family_name', '')
        )

    # Guardar info en sesión de Django
    request.session['user'] = user_info
    request.session['user_id'] = local_user.id  # ← ESTO ES CLAVE
    request.session['auth0_token'] = id_token  

    # Redirigir al frontend
    return redirect('http://localhost:3000/dashboard')


@csrf_exempt
def register_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    form = RegisterForm(data)
    if not form.is_valid():
        return JsonResponse({"error": form.errors}, status=400)

    nombre = form.cleaned_data.get("nombre", "")
    apellido = form.cleaned_data.get("apellido", "")
    email = form.cleaned_data["email"]
    password = form.cleaned_data["password"]
    calle = form.cleaned_data.get("calle", "")
    ciudad = form.cleaned_data.get("ciudad", "")
    codigo_postal = form.cleaned_data.get("codigo_postal", "")
    telefono = form.cleaned_data.get("telefono", "")

    try:
        # 1. Crear dirección
        direccion_obj = Direccion.objects.create(
            calle=calle,
            ciudad=ciudad,
            codigo_postal=codigo_postal,
        )

        # 2. Crear usuario en Auth0
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
        auth0_id = auth0_user.get("user_id")

        # 3. Crear usuario local (sin password, porque Auth0 lo maneja)
        local_user = User.objects.create(
            username=email,
            email=email,
            first_name=nombre,
            last_name=apellido,
            direccion=direccion_obj,
            telefono=telefono
            # ❌ NO pongas password aquí, Auth0 lo maneja
        )

        request.session['user_id'] = local_user.id
        request.session['email'] = email

        # Opcional: guardar el auth0_id en tu modelo
        # local_user.auth0_id = auth0_id
        # local_user.save()

        return JsonResponse({
            "message": "Usuario creado correctamente",
            "auth0_id": auth0_id,
            "local_id": local_user.id
        })

    except requests.exceptions.HTTPError as e:
        return JsonResponse({"error": str(e), "response": r.text}, status=r.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def logout_view(request):

    request.session.flush()


    logout_url = (
        f"https://{settings.AUTH0_DOMAIN}/v2/logout?"
        f"client_id={settings.AUTH0_CLIENT_ID}&"
        f"returnTo=http://localhost:3000/"  # Tu frontend
    )

    return JsonResponse({
        "message": "Logout exitoso",
        "logout_url": logout_url  # El frontend debe redirigir aquí
    })


def check_session(request):
    """Verificar si hay sesión activa"""
    if 'user_id' in request.session:
        try:
            user = User.objects.get(id=request.session['user_id'])
            return JsonResponse({
                "authenticated": True,
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "nombre": user.first_name,
                "apellido": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,

                # ← AGREGAR ESTO
                "grupo": {
                    "id": user.grupo.id_grupo,
                    "nombre": user.grupo.nombre,
                    "rol": user.rol_en_grupo
                } if user.grupo else None,

                "taller": {
                    "id": user.taller.id,
                    "nombre": user.taller.nombre
                } if user.taller else None
            })
        except User.DoesNotExist:
            request.session.flush()
            return JsonResponse({"authenticated": False}, status=401)

    return JsonResponse({"authenticated": False}, status=401)

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
    queryset = (
        User.objects
            .select_related('direccion', 'taller', 'grupo')
            .all()
    )
    serializer_class = UserSerializer

    def get_queryset(self):
        """Filtrar usuarios según permisos"""
        user_id = self.request.session.get('user_id')

        if not user_id:
            return User.objects.none()

        user = User.objects.get(id=user_id)

        # Admin del sistema ve TODOS
        if user.is_staff or user.is_superuser:
            return User.objects.all()

        # Usuario con grupo
        if user.grupo:
            # Si es admin del grupo, puede ver:
            if user.rol_en_grupo == 'admin':
                return User.objects.filter(
                    Q(id=user.id) |  # A sí mismo
                    Q(grupo=user.grupo) |  # Usuarios de su grupo
                    Q(grupo__isnull=True, taller__isnull=True)  # ← Usuarios sin asignar
                )
            else:
                # Member/viewer solo ve usuarios del grupo
                return User.objects.filter(
                    Q(id=user.id) | Q(grupo=user.grupo)
                )

        # Usuario sin grupo solo se ve a sí mismo
        return User.objects.filter(id=user.id)

    @action(detail=True, methods=['post'])
    def quitar_taller(self, request, pk=None):
        """POST /api/usuarios/{id}/quitar_taller/"""
        usuario = self.get_object()
        current_user = User.objects.get(id=request.session['user_id'])

        if not (current_user.is_staff or current_user.id == usuario.id):
            raise PermissionDenied("No tienes permiso")

        if not usuario.taller:
            return Response({"error": "El usuario no tiene taller"}, status=400)

        usuario.taller = None
        usuario.save()

        return Response({"message": "Taller desvinculado"})



    @action(detail=True, methods=['post'])
    def asignar_grupo(self, request, pk=None):
        """POST /api/usuarios/{id}/asignar_grupo/"""
        usuario = self.get_object()
        current_user = User.objects.get(id=request.session['user_id'])

        grupo_id = request.data.get('grupo_id')
        rol = request.data.get('rol', 'member')

        try:
            grupo = Grupo.objects.get(id_grupo=grupo_id)

            # Verificar permisos
            if not current_user.is_staff:
                if not (current_user.grupo and
                        current_user.grupo.id_grupo == grupo_id and
                        current_user.rol_en_grupo == 'admin'):
                    raise PermissionDenied("No tienes permiso")

            # Validar
            if usuario.taller:
                return Response({
                    "error": "El usuario ya tiene un taller"
                }, status=400)

            # Asignar
            usuario.grupo = grupo
            usuario.rol_en_grupo = rol
            usuario.save()

            return Response({
                "message": f"Usuario asignado al grupo {grupo.nombre} como {rol}"
            })

        except Grupo.DoesNotExist:
            return Response({"error": "Grupo no encontrado"}, status=404)

    @action(detail=True, methods=['post'])
    def asignar_taller(self, request, pk=None):
        """POST /api/usuarios/{id}/asignar_taller/"""
        usuario = self.get_object()
        current_user = User.objects.get(id=request.session['user_id'])

        if not (current_user.is_staff or current_user.id == usuario.id):
            raise PermissionDenied("No tienes permiso")

        taller_id = request.data.get('taller_id')

        try:
            taller = Taller.objects.get(id=taller_id)

            if usuario.grupo:
                return Response({
                    "error": "El usuario ya tiene un grupo"
                }, status=400)

            usuario.taller = taller
            usuario.rol_en_grupo = None
            usuario.save()

            return Response({
                "message": f"Usuario asignado al taller {taller.nombre}"
            })

        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)


@csrf_exempt
def force_login(request):
    """⚠️ SOLO PARA TESTING - NO USAR EN PRODUCCIÓN"""
    email = request.POST.get('email') or json.loads(request.body).get('email')

    try:
        user = User.objects.get(email=email)
        request.session['user_id'] = user.id
        request.session['email'] = user.email

        return JsonResponse({
            "message": "Login exitoso (testing)",
            "user_id": user.id,
            "username": user.username
        })
    except User.DoesNotExist:
        return JsonResponse({"error": "Usuario no encontrado"}, status=404)
