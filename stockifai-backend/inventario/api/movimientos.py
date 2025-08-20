from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from inventario.models import Deposito, Movimiento


class MovimientosListView(APIView):

    def get(self, request, taller_id: int):
        """
                GET /talleres/<taller_id>/movimientos
                Query params opcionales:
                  - deposito_id: int
                  - q: str  (numero_pieza | sku | nombre | descripcion)
                  - date_from: YYYY-MM-DD
                  - date_to:   YYYY-MM-DD
                  - page: int (default 1)
                  - page_size: int (default 50, máx 200)
        """

        deposito_id = request.query_params.get("deposito_id")
        q = request.query_params.get("q")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

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
        ).filter(stock_por_deposito__repuesto_taller__taller_id=taller_id)

        sql = queryset.query

        resultados = queryset.all()




        return Response({"results": resultados}, status=status.HTTP_200_OK)