from user.api.models.models import User

def get_user_from_request(request):
    """
    Obtiene el usuario desde la sesión o usa uno por defecto para testing
    """
    user_id = request.session.get('user_id')
    if user_id:
        return User.objects.get(id=user_id)
    else:
        # Para testing: usa el primer usuario
        return User.objects.first()