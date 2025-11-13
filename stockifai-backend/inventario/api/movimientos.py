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
from user.api.models.models import Taller, GrupoTaller


class MovimientosListView(APIView):

    def get(self, request, taller_id: int):
        """
        GET /talleres/<taller_id>/movimientos
        Si el taller pertenece a un grupo (a través de GrupoTaller),
        muestra movimientos de TODOS los talleres del grupo.
        Si es un taller individual, muestra solo sus movimientos.
        """

        deposito_id = request.query_params.get("deposito_id")
        search_query = request.query_params.get("search_text")
        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")

        # Paginacion
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        try:
            # Verificar que el taller existe
            taller = Taller.objects.get(pk=taller_id)

            """"
            # 🔧 CAMBIO: Usar id_taller en lugar de taller_id
            grupo_taller = GrupoTaller.objects.filter(id_taller=taller_id).first()

            # Obtener todos los talleres relevantes
            if grupo_taller:
                # 🔧 CAMBIO: Usar id_grupo e id_taller
                talleres_ids = list(GrupoTaller.objects.filter(
                    id_grupo=grupo_taller.id_grupo
                ).values_list('id_taller', flat=True))
            else:
                talleres_ids = [taller_id]
            """

            talleres_ids = [int(taller_id)]

            # Validar depósito
            if deposito_id:
                deposito_exists = Deposito.objects.filter(
                    pk=deposito_id,
                    taller_id__in=talleres_ids  # Este está bien, Deposito sí usa taller_id
                ).exists()

                if not deposito_exists:
                    return Response(
                        {"detail": "Depósito inválido para este taller/grupo"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Construir queryset
            queryset = Movimiento.objects.select_related(
                "stock_por_deposito__deposito",
                "stock_por_deposito__repuesto_taller__taller",
                "stock_por_deposito__repuesto_taller__repuesto",
                "stock_por_deposito__repuesto_taller__repuesto__marca",
                "stock_por_deposito__repuesto_taller__repuesto__categoria",
            ).filter(
                stock_por_deposito__repuesto_taller__taller_id__in=talleres_ids
            )

            # Filtro por depósito específico
            if deposito_id:
                queryset = queryset.filter(stock_por_deposito__deposito_id=deposito_id)

            # Búsqueda por texto
            if search_query:
                queryset = queryset.filter(
                    Q(stock_por_deposito__repuesto_taller__repuesto__numero_pieza__icontains=search_query)
                    | Q(stock_por_deposito__repuesto_taller__repuesto__descripcion__icontains=search_query)
                )

            # Filtros de fecha
            tz = timezone.get_current_timezone()

            if date_from_str:
                date_from = parse_date(date_from_str)
                start_dt = timezone.make_aware(datetime.combine(date_from, time.min), tz)
                queryset = queryset.filter(fecha__gte=start_dt)

            if date_to_str:
                date_to = parse_date(date_to_str)
                end_next = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min), tz)
                queryset = queryset.filter(fecha__lt=end_next)

            queryset = queryset.order_by("-fecha", "stock_por_deposito__repuesto_taller__repuesto__descripcion")

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

        except Taller.DoesNotExist:
            return Response(
                {"detail": "Taller no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )