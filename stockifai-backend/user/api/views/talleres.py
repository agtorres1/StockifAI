from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError

from inventario.models import Movimiento
from user.api.serializers.taller_serializer import TallerSerializer
from user.api.models.models import Taller, User, GrupoTaller
from user.permissions import PermissionChecker

class TallerViewSet(viewsets.ModelViewSet):
    queryset = Taller.objects.all()  # ← AGREGAR ESTO
    serializer_class = TallerSerializer

    def get_queryset(self):
        """Filtrar talleres según permisos (para listar/ver)"""
        user_id = self.request.session.get('user_id')

        if not user_id:
            return Taller.objects.none()

        try:
            user = User.objects.get(id=user_id)

            # Admin ve TODO
            if user.is_staff or user.is_superuser:
                return Taller.objects.all()

            # Construir lista de talleres que puede ver
            talleres_ids = set()

            # Su taller personal
            if user.taller:
                talleres_ids.add(user.taller.id)

            # Talleres de su grupo
            if user.grupo:
                talleres_grupo = GrupoTaller.objects.filter(
                    id_grupo=user.grupo
                ).values_list('id_taller', flat=True)
                talleres_ids.update(talleres_grupo)

            return Taller.objects.filter(id__in=talleres_ids)

        except User.DoesNotExist:
            return Taller.objects.none()

    def perform_create(self, serializer):
        user = User.objects.get(id=self.request.session['user_id'])

        # Crear el taller
        taller = serializer.save()

        # Si el usuario pertenece a un grupo, crear la relación en GrupoTaller
        if user.grupo:
            GrupoTaller.objects.create(
                id_grupo=user.grupo,
                id_taller=taller
            )
            print(f"✅ Taller '{taller.nombre}' asignado al grupo '{user.grupo.nombre}'")

        # Si el usuario NO tiene grupo NI taller, asignárselo directamente
        elif not user.taller:
            user.taller = taller
            user.save()
            print(f"✅ Taller '{taller.nombre}' asignado al usuario '{user.username}'")

        # Si ya tiene taller pero no grupo, error
        else:
            raise ValidationError("Ya tienes un taller asignado")

    def retrieve(self, request, *args, **kwargs):
        """Ver un taller"""
        taller = self.get_object()
        user = User.objects.get(id=request.session['user_id'])

        if not PermissionChecker.puede_ver_taller(user, taller):
            raise PermissionDenied("No tienes permiso para ver este taller")

        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Editar un taller"""
        taller = self.get_object()
        user = User.objects.get(id=request.session['user_id'])

        if not PermissionChecker.puede_editar_taller(user, taller):
            raise PermissionDenied("No tienes permiso para editar este taller")

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminar un taller"""
        print("🔍 DEBUG - Entrando a destroy")

        try:
            taller = self.get_object()
            print(f"🔍 DEBUG - Taller obtenido: {taller.id}")
        except Exception as e:
            print(f"❌ ERROR al obtener taller: {e}")
            raise

        try:
            user = User.objects.get(id=request.session['user_id'])
            print(f"🔍 DEBUG - Usuario obtenido: {user.username}")
        except Exception as e:
            print(f"❌ ERROR al obtener usuario: {e}")
            raise

        try:
            puede = PermissionChecker.puede_eliminar_taller(user, taller)
            print(f"🔍 DEBUG - puede_eliminar_taller: {puede}")
        except Exception as e:
            print(f"❌ ERROR en puede_eliminar_taller: {e}")
            raise

        if not puede:
            raise PermissionDenied("No tienes permiso para eliminar este taller")

        print("🔍 DEBUG - Llamando a super().destroy()")
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            print(f"❌ ERROR en super().destroy(): {e}")
            raise


class TallerView(APIView):
    """
    GET /talleres/<taller_id>/info
    Respuesta:
    {
      "taller": { ...datos básicos... },
      "stock_inicial_cargado": true|false
    }
    """

    def get(self, request, taller_id: int):
        try:
            taller = Taller.objects.get(pk=taller_id)
        except Taller.DoesNotExist:
            return Response(
                {"detail": "Taller no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        stock_inicial_cargado = Movimiento.objects.filter(
            stock_por_deposito__repuesto_taller__taller_id=taller.id
        ).exists()

        data = {
            "taller": TallerSerializer(taller).data,
            "stock_inicial_cargado": stock_inicial_cargado,
        }
        return Response(data, status=status.HTTP_200_OK)
