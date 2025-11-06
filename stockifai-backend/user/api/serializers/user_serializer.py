from rest_framework import serializers

from inventario.api.serializers import TallerSerializer
from user.api.serializers.grupo_serializer import GrupoSerializer
from user.models import User, Direccion, Taller, Grupo


class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    direccion = DireccionSerializer(required=False, allow_null=True)
    taller = TallerSerializer(read_only=True)
    grupo = GrupoSerializer(read_only=True)

    id_taller = serializers.PrimaryKeyRelatedField(
        source='taller', queryset=Taller.objects.all(),
        allow_null=True, required=False, write_only=True
    )

    id_grupo = serializers.PrimaryKeyRelatedField(
        source='grupo', queryset=Grupo.objects.all(),
        allow_null=True, required=False, write_only=True
    )

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "telefono",
            "taller", "grupo", "direccion",
            "id_taller", "id_grupo",
            "rol_en_grupo", "rol_en_taller",
        ]

    def create(self, validated_data):
        direccion_data = validated_data.pop("direccion", None)
        user = User.objects.create(**validated_data)
        if direccion_data:
            direccion = Direccion.objects.create(**direccion_data)
            user.direccion = direccion
            user.save()
        return user

    def update(self, instance, validated_data):
        direccion_data = validated_data.pop("direccion", None)

        # Limpiar taller si se asigna grupo y viceversa
        if 'grupo' in validated_data and validated_data.get('grupo'):
            instance.taller = None
            instance.rol_en_taller = None  # ← AGREGAR: Limpiar rol de taller
            if not validated_data.get('rol_en_grupo'):
                validated_data['rol_en_grupo'] = 'member'

        if 'taller' in validated_data and validated_data.get('taller'):
            instance.grupo = None
            instance.rol_en_grupo = None
            if not validated_data.get('rol_en_taller'):  # ← AGREGAR: Asignar rol por defecto
                validated_data['rol_en_taller'] = 'member'

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if direccion_data:
            if instance.direccion:
                for attr, value in direccion_data.items():
                    setattr(instance.direccion, attr, value)
                instance.direccion.save()
            else:
                direccion = Direccion.objects.create(**direccion_data)
                instance.direccion = direccion
                instance.save()

        return instance