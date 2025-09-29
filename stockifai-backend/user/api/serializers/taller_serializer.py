from rest_framework import serializers
from user.api.models.models import Taller


class TallerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taller
        fields = ("id", "nombre", "direccion", "telefono", "email", "fecha_creacion")
