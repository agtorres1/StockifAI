from rest_framework import serializers
from user.api.models.models import Grupo, GrupoTaller, Taller


class TallerSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple para mostrar info básica del taller"""

    class Meta:
        model = Taller
        fields = ['id', 'nombre', 'direccion', 'telefono', 'email']


class GrupoSerializer(serializers.ModelSerializer):
    talleres = serializers.SerializerMethodField()

    class Meta:
        model = Grupo
        fields = ['id_grupo', 'nombre', 'descripcion', 'grupo_padre', 'talleres']

    def get_talleres(self, obj):
        """Obtener talleres asociados a través de la tabla intermedia GrupoTaller"""
        # Buscar todas las relaciones GrupoTaller para este grupo
        grupo_talleres = GrupoTaller.objects.filter(id_grupo=obj).select_related('id_taller')

        # Extraer los objetos Taller
        talleres = [gt.id_taller for gt in grupo_talleres]

        # Serializar y devolver
        return TallerSimpleSerializer(talleres, many=True).data


class GrupoTallerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoTaller
        fields = '__all__'


