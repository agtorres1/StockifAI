from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from .jwt_utils import decode_jwt

class Auth0JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Ignorar admin
        if not request.path.startswith("/api/"):
            return None  # deja que Django maneje otras rutas (/admin/)

        auth_header = request.headers.get("Authorization")
        #if not auth_header:
        #    raise AuthenticationFailed("Token requerido")

        parts = auth_header.split()
        if parts[0].lower() != "bearer" or len(parts) != 2:
            raise AuthenticationFailed("Header Authorization inválido")

        token = parts[1]

        try:
            payload = decode_jwt(token)
        except Exception as e:
            raise AuthenticationFailed(f"Token inválido: {str(e)}")

        return (AnonymousUser(), payload)
