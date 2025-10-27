from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from inventario.models import Movimiento
from user.api.serializers.taller_serializer import TallerSerializer
<<<<<<< HEAD
from user.api.models.models import Taller
from rest_framework.decorators import action
from user.api.models.models import User
=======
from user.models import Taller

>>>>>>> origin/main

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

        if user.grupo:
            raise ValidationError("Ya perteneces a un grupo")

        if user.taller:
            raise ValidationError("Ya tienes un taller")

        taller = serializer.save()
        user.taller = taller
        user.save()

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
        taller = self.get_object()
        user = User.objects.get(id=request.session['user_id'])

        if not PermissionChecker.puede_eliminar_taller(user, taller):
            raise PermissionDenied("No tienes permiso para eliminar este taller")

        return super().destroy(request, *args, **kwargs)

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
