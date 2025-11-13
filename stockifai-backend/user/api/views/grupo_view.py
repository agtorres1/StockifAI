from rest_framework import viewsets
from rest_framework.decorators import action

from user.api.models.models import Grupo, GrupoTaller, User, Taller
from user.api.serializers.grupo_serializer import GrupoSerializer, GrupoTallerSerializer

from rest_framework.exceptions import PermissionDenied
from user.permissions import PermissionChecker
from rest_framework.response import Response


class GrupoViewSet(viewsets.ModelViewSet):
    queryset = Grupo.objects.all()  # ← AGREGAR ESTO
    serializer_class = GrupoSerializer

    @action(detail=True, methods=['post'])
    def desasignar_taller(self, request, pk=None):
        """Desasignar taller del grupo"""
        grupo = self.get_object()
        user = User.objects.get(id=request.session['user_id'])

        if not PermissionChecker.puede_gestionar_grupo(user, grupo):
            raise PermissionDenied("No tienes permiso")

        taller_id = request.data.get('taller_id')

        try:
            taller = Taller.objects.get(id=taller_id)

            # Eliminar la relación
            GrupoTaller.objects.filter(
                id_grupo=grupo,
                id_taller=taller
            ).delete()

            return Response({
                "message": f"Taller {taller.nombre} desasignado del grupo"
            })

        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)

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
        """Al crear grupo, el usuario es admin automáticamente (excepto superuser)"""
        user = User.objects.get(id=self.request.session['user_id'])

        # ✅ NO asignar al superuser automáticamente
        if user.is_superuser or user.is_staff:
            grupo = serializer.save()
            print(f"✅ Superuser {user.username} creó el grupo {grupo.nombre} sin asignarse")
            return

        # ← Validaciones para usuarios normales
        if user.grupo:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                "error": "Ya perteneces a un grupo. No puedes crear otro."
            })

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
        print("📥 Entró a asignar_taller")
        grupo = self.get_object()
        print("✅ Grupo obtenido:", grupo)

        try:
            user = User.objects.get(id=request.session['user_id'])
        except Exception as e:
            print("❌ Error obteniendo user:", e)
            raise

        print("👤 Usuario:", user)

        if not PermissionChecker.puede_gestionar_grupo(user, grupo):
            raise PermissionDenied("No tienes permiso")

        taller_id = request.data.get('taller_id')
        print("🧱 ID taller recibido:", taller_id)

        try:
            taller = Taller.objects.get(id=taller_id)
            print("🎯 Taller encontrado:", taller)

            GrupoTaller.objects.create(id_grupo=grupo, id_taller=taller)
            print("✅ Relación creada correctamente")

            return Response({"message": f"Taller {taller.nombre} asignado al grupo"})

        except Exception as e:
            print("💥 Error asignando taller:", e)
            raise


class GrupoTallerViewSet(viewsets.ModelViewSet):
    queryset = GrupoTaller.objects.all()
    serializer_class = GrupoTallerSerializer
    