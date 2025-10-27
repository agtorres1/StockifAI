# users/middleware.py
from django.http import JsonResponse

from django.http import JsonResponse

# user/middleware.py

from django.http import JsonResponse


class Auth0Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ← AGREGAR ESTO TEMPORAL
        print(f"🔍 Path: {request.path}")
        print(f"🔍 Session user_id: {request.session.get('user_id')}")

        # Rutas públicas (sin autenticación requerida)
        public_paths = [
            '/api/register/',
            '/api/login/',
            '/api/callback/',
            '/api/logout/',
            '/api/check-session/',
            '/admin/',
            '/static/',
            '/api/force-login/',
            '/media/',
        ]

        # Si la ruta es pública, permitir acceso
        if any(request.path.startswith(path) for path in public_paths):
            print("✅ Ruta pública - permitiendo acceso")
            return self.get_response(request)

        # Si no hay sesión activa, bloquear
        if 'user_id' not in request.session:
            print("❌ Sin sesión - bloqueando")
            return JsonResponse({
                "error": "No autenticado",
                "message": "Debes iniciar sesión para acceder a este recurso"
            }, status=401)

        # Si hay sesión, permitir acceso
        response = self.get_response(request)
        return response