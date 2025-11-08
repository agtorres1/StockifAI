# user/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from user.api.models.models import Taller, User


class SessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        user_id = request.session.get('user_id')

        if not user_id:
            return None

        try:
            user = User.objects.get(id=user_id)
            return (user, None)
        except User.DoesNotExist:
            raise AuthenticationFailed('Usuario no encontrado')