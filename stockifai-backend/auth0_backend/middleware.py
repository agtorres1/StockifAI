from django.http import JsonResponse
from .auth import decode_jwt

EXCLUDE_PATHS = ["/user/login/", "/user/callback/", "/admin/"]

def jwt_middleware(get_response):
    def middleware(request):
        # Ignorar rutas excluidas
        if any(request.path.startswith(p) for p in EXCLUDE_PATHS):
            return get_response(request)

        auth = request.headers.get("Authorization", None)

        if not auth:
            return JsonResponse({"error": "Token requerido"}, status=401)

        parts = auth.split()
        if parts[0].lower() != "bearer" or len(parts) != 2:
            return JsonResponse({"error": "Formato inválido"}, status=401)

        token = parts[1]
        try:
            payload = decode_jwt(token)
            request.user = payload  # lo guardamos en request
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=401)

        return get_response(request)
    return middleware
