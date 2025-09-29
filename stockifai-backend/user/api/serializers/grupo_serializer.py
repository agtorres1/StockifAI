from rest_framework import serializers
from user.api.models.models import Grupo, GrupoTaller


class GrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grupo
        fields = '__all__'


class GrupoTallerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoTaller
        fields = '__all__'


