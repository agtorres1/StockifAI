from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from catalogo.models import Categoria
from inventario.api.serializers import CategoriaSerializer


class CategoriasListView(APIView):
    """
    GET /categorias
    Devuelve todas las categorías.
    """
    def get(self, request):
        queryset = Categoria.objects.all().order_by("nombre")
        serializer = CategoriaSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
