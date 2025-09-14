from datetime import datetime, time, timedelta
from django.utils.dateparse import parse_date
from django.utils import timezone

from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from inventario.api.serializers import MovimientosSerializer
from inventario.models import Deposito, Movimiento


class MovimientosListView(APIView):

    def get(self, request, taller_id: int):
        """
                GET /talleres/<taller_id>/movimientos
                Query params opcionales:
                  - deposito_id: int
                  - search_text: str  (numero_pieza | sku | nombre | descripcion)
                  - date_from: YYYY-MM-DD
                  - date_to:   YYYY-MM-DD
                  - page: int (default 1)
                  - page_size: int (default 10, máx 200)
        """

        deposito_id = request.query_params.get("deposito_id")
        search_query = request.query_params.get("search_text")
        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")

        # Paginacion
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if deposito_id:
            if not Deposito.objects.filter(pk=deposito_id, taller_id=taller_id).exists():
                return Response({"detail": "Depósito inválido para el taller"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Movimiento.objects.select_related(
            "stock_por_deposito__deposito",
            "stock_por_deposito__repuesto_taller__taller",
            "stock_por_deposito__repuesto_taller__repuesto",
            "stock_por_deposito__repuesto_taller__repuesto__marca",
            "stock_por_deposito__repuesto_taller__repuesto__categoria",
        ).filter(stock_por_deposito__repuesto_taller__taller_id=taller_id)

        if deposito_id:
            queryset = queryset.filter(stock_por_deposito__deposito_id=deposito_id)

        if search_query:
            queryset = queryset.filter(
                Q(stock_por_deposito__repuesto_taller__repuesto__numero_pieza__icontains=search_query)
                | Q(stock_por_deposito__repuesto_taller__repuesto__descripcion__icontains=search_query)
            )

        tz = timezone.get_current_timezone()

        if date_from_str:
            date_from = parse_date(date_from_str) if date_from_str else None
            start_dt = timezone.make_aware(datetime.combine(date_from, time.min), tz)
            queryset = queryset.filter(fecha__gte=start_dt)
        if date_to_str:
            date_to = parse_date(date_to_str) if date_to_str else None
            end_next = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min), tz)
            queryset = queryset.filter(fecha__lt=end_next)

        queryset = queryset.order_by("-fecha", "-id")

        # Paginacion
        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = MovimientosSerializer(page_obj.object_list, many=True)

        response = {
            "count": paginator.count,
            "page": page_obj.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "results": serializer.data,
        }

        return Response(response, status=status.HTTP_200_OK)