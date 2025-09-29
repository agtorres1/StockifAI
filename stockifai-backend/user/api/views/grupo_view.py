from rest_framework import viewsets
from user.api.models.models import Grupo, GrupoTaller
from user.api.serializers.grupo_serializer import GrupoSerializer, GrupoTallerSerializer

class GrupoViewSet(viewsets.ModelViewSet):
    queryset = Grupo.objects.all()
    serializer_class = GrupoSerializer

class GrupoTallerViewSet(viewsets.ModelViewSet):
    queryset = GrupoTaller.objects.all()
    serializer_class = GrupoTallerSerializer
    