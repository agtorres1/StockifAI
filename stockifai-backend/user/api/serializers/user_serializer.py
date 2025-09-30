from rest_framework import serializers
from user.models import User, Direccion


class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    direccion = DireccionSerializer(required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "telefono", "taller", "grupo", "direccion"
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