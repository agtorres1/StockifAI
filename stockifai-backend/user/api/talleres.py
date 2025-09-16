from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from inventario.models import Movimiento
from user.api.serializers import TallerSerializer
from user.models import Taller


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
