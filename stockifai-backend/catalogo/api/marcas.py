from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from catalogo.models import Marca
from inventario.api.serializers import MarcaSerializer

class MarcasListView(APIView):
    """
    GET /marcas
    Devuelve todas las marcas.
    """
    def get(self, request):
        queryset = Marca.objects.all().order_by("nombre")
        serializer = MarcaSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)