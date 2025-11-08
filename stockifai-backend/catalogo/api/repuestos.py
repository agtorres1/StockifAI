from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Repuesto
from inventario.api.serializers import RepuestoSerializer
from user.permissions import PermissionChecker  # ← IMPORTAR


class RepuestosListView(APIView):
    """"
    GET /repuestos
    Devuelve repuestos según permisos del usuario
    """

    def get(self, request):
        # ===== AGREGAR FILTRO DE PERMISOS =====
        user = PermissionChecker.get_user_from_session(request)

        queryset = Repuesto.objects.select_related("marca", "categoria")
        queryset = PermissionChecker.filter_repuestos_queryset(queryset, user)
        # ===== FIN FILTRO =====

        # Parámetros de paginación
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        search_query = request.query_params.get("search_text")
        marca_id = request.query_params.get("marca_id")
        categoria_id = request.query_params.get("categoria_id")

        # Filtros adicionales
        if marca_id:
            queryset = queryset.filter(marca__id=marca_id)

        if categoria_id:
            queryset = queryset.filter(categoria__id=categoria_id)

        if search_query:
            queryset = queryset.filter(
                Q(numero_pieza__icontains=search_query)
                | Q(descripcion__icontains=search_query)
            )

        queryset = queryset.order_by("descripcion")

        # Paginación
        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = RepuestoSerializer(page_obj.object_list, many=True)

        repuestos = {
            "count": paginator.count,
            "page": page_obj.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "results": serializer.data,
        }

        return Response(repuestos, status=status.HTTP_200_OK)