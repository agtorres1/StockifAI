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
def login_with_credentials(request):
    """Login directo con email/password usando Auth0"""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        print(f"🔍 Intentando login con: {email}")

        # Autenticar con Auth0 usando Resource Owner Password
        auth_response = requests.post(
            f"https://{settings.AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "password",
                "username": email,
                "password": password,
                "client_id": settings.AUTH0_CLIENT_ID,
                "client_secret": settings.AUTH0_CLIENT_SECRET,
                "audience": settings.AUTH0_AUDIENCE,
                "scope": "openid profile email",
                "realm": "Username-Password-Authentication"
            }
        )

        print(f"🔍 Status code de Auth0: {auth_response.status_code}")
        print(f"🔍 Respuesta de Auth0: {auth_response.text}")

        if auth_response.status_code != 200:
            return JsonResponse({
                "error": "Credenciales inválidas",
                "details": auth_response.text
            }, status=401)

        tokens = auth_response.json()
        id_token = tokens.get('id_token')

        # Decodificar token
        user_info = jwt.decode(id_token, options={"verify_signature": False})
        email = user_info.get('email')

        # MODIFICAR: Buscar usuario con select_related
        try:
            local_user = User.objects.select_related('taller', 'grupo').get(email=email)
        except User.DoesNotExist:
            local_user = User.objects.create(
                username=email,
                email=email,
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', '')
            )

        # Guardar en sesión
        request.session['user_id'] = local_user.id
        request.session['email'] = email

        # AGREGAR DEBUG
        print(f"👤 Usuario: {local_user.username}")
        print(f"🏭 Taller: {local_user.taller}")
        print(f"📦 Grupo: {local_user.grupo}")

        print(f"🔍 DEBUG - rol_en_taller: {local_user.rol_en_taller}")
        print(f"🔍 DEBUG - taller objeto: {local_user.taller}")

        grupo_data = None
        if local_user.grupo:
            from user.models import GrupoTaller
            talleres_grupo = GrupoTaller.objects.filter(
                id_grupo=local_user.grupo
            ).select_related('id_taller')

            grupo_data = {
                "id_grupo": local_user.grupo.id_grupo,
                "nombre": local_user.grupo.nombre,
                "rol": local_user.rol_en_grupo,
                "talleres": [
                    {"id": gt.id_taller.id, "nombre": gt.id_taller.nombre}
                    for gt in talleres_grupo
                ]
            }




        return JsonResponse({
            "authenticated": True,
            "user_id": local_user.id,
            "email": local_user.email,
            "username": local_user.username,
            "nombre": local_user.first_name,      # ✅ CAMBIAR
            "apellido": local_user.last_name,
            "is_staff": local_user.is_staff,
            "is_superuser": local_user.is_superuser,
            "grupo": grupo_data,
            "taller": {
                "id": local_user.taller.id,
                "nombre": local_user.taller.nombre,
                "rol": local_user.rol_en_taller
            } if local_user.taller else None,

        })

    except Exception as e:
        print(f"❌ Error en login: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)




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
    return redirect('http://localhost:4200/callback')


@csrf_exempt
def register_api(request):
    """Admin crea un usuario y lo registra en Auth0"""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    # Obtener datos del formulario
    nombre = data.get("first_name", "")
    apellido = data.get("last_name", "")
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    telefono = data.get("telefono", "")

    # Dirección
    direccion_data = data.get("direccion", {})
    calle = direccion_data.get("calle", "")
    ciudad = direccion_data.get("ciudad", "")
    codigo_postal = direccion_data.get("codigo_postal", "")

    # Taller/Grupo/Roles
    id_taller = data.get("id_taller")
    id_grupo = data.get("id_grupo")
    rol_en_taller = data.get("rol_en_taller")
    rol_en_grupo = data.get("rol_en_grupo")

    # Validaciones básicas
    if not email or not password or not username:
        return JsonResponse({
            "error": "Email, username y contraseña son requeridos"
        }, status=400)

    if len(password) < 8:
        return JsonResponse({
            "error": "La contraseña debe tener al menos 8 caracteres"
        }, status=400)

    direccion_obj = None
    local_user = None

    try:
        # 1. Crear dirección
        direccion_obj = Direccion.objects.create(
            calle=calle,
            ciudad=ciudad,
            codigo_postal=codigo_postal,
            pais='Argentina'
        )
        print(f"✅ Dirección creada: ID={direccion_obj.id_direccion}")

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

        if r.status_code == 409:
            # Limpiar si el email ya existe
            if direccion_obj:
                direccion_obj.delete()
            return JsonResponse({
                "error": "Este email ya está registrado en Auth0."
            }, status=409)

        r.raise_for_status()
        auth0_user = r.json()
        auth0_id = auth0_user.get("user_id")
        print(f"✅ Usuario creado en Auth0: {auth0_id}")

        # 3. Crear usuario local
        local_user = User(
            username=username,
            email=email,
            first_name=nombre,
            last_name=apellido,
            telefono=telefono,
            direccion=direccion_obj,
            taller_id=id_taller if id_taller else None,
            grupo_id=id_grupo if id_grupo else None,
            rol_en_taller=rol_en_taller if id_taller else None,
            rol_en_grupo=rol_en_grupo if id_grupo else None,
        )

        # Guardar sin ejecutar clean() para evitar conflictos
        local_user.save(force_insert=True)
        print(f"✅ Usuario local creado: ID={local_user.id}")

        return JsonResponse({
            "message": "Usuario creado correctamente",
            "auth0_id": auth0_id,
            "user": {
                "id": local_user.id,
                "username": local_user.username,
                "email": local_user.email,
                "first_name": local_user.first_name,
                "last_name": local_user.last_name,
            }
        }, status=201)

    except requests.exceptions.HTTPError as e:
        # Limpiar si Auth0 falla
        if direccion_obj:
            direccion_obj.delete()

        return JsonResponse({
            "error": "Error al crear usuario en Auth0",
            "details": r.text
        }, status=r.status_code)

    except Exception as e:
        # Rollback: eliminar todo lo creado
        if local_user and local_user.id:
            local_user.delete()
        if direccion_obj and direccion_obj.id_direccion:
            direccion_obj.delete()

        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def logout_view(request):

    request.session.flush()


    logout_url = (
        f"https://{settings.AUTH0_DOMAIN}/v2/logout?"
        f"client_id={settings.AUTH0_CLIENT_ID}&"
        f"returnTo=http://localhost:4200/"  # Tu frontend
    )

    return JsonResponse({
        "message": "Logout exitoso",
        "logout_url": logout_url  # El frontend debe redirigir aquí
    })


def check_session(request):
    """Verificar si hay sesión activa"""
    if 'user_id' in request.session:
        try:
            user = User.objects.select_related('taller', 'grupo').get(id=request.session['user_id'])

            # Obtener talleres del grupo
            grupo_data = None
            if user.grupo:
                from user.models import GrupoTaller
                talleres_grupo = GrupoTaller.objects.filter(
                    id_grupo=user.grupo
                ).select_related('id_taller')

                grupo_data = {
                    "id_grupo": user.grupo.id_grupo,
                    "nombre": user.grupo.nombre,
                    "rol": user.rol_en_grupo,
                    "talleres": [
                        {"id": gt.id_taller.id, "nombre": gt.id_taller.nombre}
                        for gt in talleres_grupo
                    ]
                }

            return JsonResponse({
                "authenticated": True,
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "nombre": user.first_name,
                "apellido": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "grupo": grupo_data,
                "taller": {
                    "id": user.taller.id,
                    "nombre": user.taller.nombre,
                    "rol": user.rol_en_taller
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

        user = User.objects.select_related('taller', 'grupo').get(id=user_id)

        # Admin del sistema ve TODOS
        if user.is_staff or user.is_superuser:
            return User.objects.select_related('taller', 'grupo', 'direccion').all()

        # Usuario con grupo
        if user.grupo:
            # Si es admin del grupo, puede ver:
            if user.rol_en_grupo == 'admin':
                # Obtener talleres del grupo
                from user.models import GrupoTaller
                talleres_ids = GrupoTaller.objects.filter(
                    id_grupo=user.grupo
                ).values_list('id_taller', flat=True)

                return User.objects.select_related('taller', 'grupo', 'direccion').filter(
                    Q(id=user.id) |  # A sí mismo
                    Q(grupo=user.grupo) |  # Usuarios del grupo
                    Q(taller__id__in=talleres_ids)  # Usuarios de talleres del grupo
                )
            else:
                # Member/viewer solo ve usuarios del grupo
                return User.objects.select_related('taller', 'grupo', 'direccion').filter(
                    Q(id=user.id) | Q(grupo=user.grupo)
                )

        # Usuario con taller (owner)
        if user.taller and user.rol_en_taller == 'owner':
            return User.objects.select_related('taller', 'grupo', 'direccion').filter(
                taller=user.taller
            )

        # Usuario sin grupo solo se ve a sí mismo
        return User.objects.select_related('taller', 'grupo', 'direccion').filter(id=user.id)

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
    def asignar_taller(self, request, pk=None):
        """Asignar taller al grupo"""
        try:
            print("📥 Entró a asignar_taller")

            grupo = self.get_object()
            print(f"✅ Grupo obtenido: {grupo.nombre}")

            user = User.objects.get(id=request.session['user_id'])
            print(f"👤 Usuario: {user.email}")

            # Verificar permisos
            if not PermissionChecker.puede_gestionar_grupo(user, grupo):
                print("🚫 Sin permisos")
                raise PermissionDenied("No tienes permiso")

            # Obtener taller_id del request
            taller_id = request.data.get('taller_id')
            print(f"🔍 Taller ID recibido: {taller_id}")

            # Verificar si existe
            from user.api.models.models import Taller  # Asegurate de importar si no está
            taller = Taller.objects.get(id=taller_id)
            print(f"✅ Taller encontrado: {taller.nombre}")

            # Crear relación
            GrupoTaller.objects.create(
                id_grupo=grupo,
                id_taller=taller
            )
            print("✅ Relación Grupo-Taller creada correctamente")

            return Response({
                "message": f"Taller {taller.nombre} asignado al grupo"
            })

        except Exception as e:
            import traceback
            print("❌ ERROR EN asignar_taller:")
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=500)



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
