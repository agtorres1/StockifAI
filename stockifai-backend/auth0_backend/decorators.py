from functools import wraps
from django.http import JsonResponse
from .auth import verify_jwt

def requires_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth = request.headers.get("Authorization", None)
        if not auth:
            return JsonResponse({"message": "Missing authorization header"}, status=401)
        parts = auth.split()
        if parts[0].lower() != "bearer":
            return JsonResponse({"message": "Invalid header"}, status=401)
        token = parts[1]
        try:
            payload = verify_jwt(token)
            request.user_payload = payload  # opcional: pasar info del usuario a la vista
        except Exception as e:
            return JsonResponse({"message": str(e)}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper
