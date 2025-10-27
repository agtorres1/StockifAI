from rest_framework import viewsets
<<<<<<< HEAD
from user.api.models.models import Grupo, GrupoTaller, User
=======
from user.models import Grupo, GrupoTaller
>>>>>>> origin/main
from user.api.serializers.grupo_serializer import GrupoSerializer, GrupoTallerSerializer
from rest_framework.decorators import action

class GrupoViewSet(viewsets.ModelViewSet):
    queryset = Grupo.objects.all()  # ← AGREGAR ESTO
    serializer_class = GrupoSerializer

    def get_queryset(self):
        """Filtrar grupos"""
        user_id = self.request.session.get('user_id')

        if not user_id:
            return Grupo.objects.none()

        user = User.objects.get(id=user_id)

        # Admin ve todo
        if user.is_staff or user.is_superuser:
            return Grupo.objects.all()

        # Usuario normal solo ve SU grupo
        if user.grupo:
            return Grupo.objects.filter(id_grupo=user.grupo.id_grupo)

        return Grupo.objects.none()

    def perform_create(self, serializer):
        """Al crear grupo, el usuario es admin automáticamente"""
        user = User.objects.get(id=self.request.session['user_id'])

        # ← AGREGAR ESTA VALIDACIÓN
        if user.grupo:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                "error": "Ya perteneces a un grupo. No puedes crear otro."
            })

        # Validar que no tenga taller
        if user.taller:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                "error": "Ya tienes un taller. Debes quitarlo primero para crear un grupo."
            })

        grupo = serializer.save()

        # Asignar al usuario como admin del grupo
        user.grupo = grupo
        user.rol_en_grupo = 'admin'
        user.save()

        print(f"✅ {user.username} creó el grupo {grupo.nombre} y es admin")

    @action(detail=True, methods=['get'])
    def miembros(self, request, pk=None):
        """Ver miembros del grupo"""
        grupo = self.get_object()
        user = User.objects.get(id=request.session['user_id'])

        if not PermissionChecker.puede_ver_grupo(user, grupo):
            raise PermissionDenied("No tienes permiso")

        miembros = User.objects.filter(grupo=grupo)

        return Response({
            "grupo": grupo.nombre,
            "miembros": [
                {
                    "user_id": m.id,
                    "username": m.username,
                    "email": m.email,
                    "rol_en_grupo": m.rol_en_grupo
                }
                for m in miembros
            ]
        })

    @action(detail=True, methods=['post'])
    def asignar_taller(self, request, pk=None):
        """Asignar taller al grupo"""
        grupo = self.get_object()
        user = User.objects.get(id=request.session['user_id'])

        if not PermissionChecker.puede_gestionar_grupo(user, grupo):
            raise PermissionDenied("No tienes permiso")

        taller_id = request.data.get('taller_id')

        try:
            taller = Taller.objects.get(id=taller_id)

            GrupoTaller.objects.create(
                id_grupo=grupo,
                id_taller=taller
            )

            return Response({
                "message": f"Taller {taller.nombre} asignado al grupo"
            })

        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)




class GrupoTallerViewSet(viewsets.ModelViewSet):
    queryset = GrupoTaller.objects.all()
    serializer_class = GrupoTallerSerializer
    