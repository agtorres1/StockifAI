from rest_framework import serializers

from inventario.models import Deposito


class MovimientosImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    fields_map = serializers.JSONField(required=False)
    taller_id = serializers.IntegerField()
    deposito_nombre = serializers.CharField(required=False)
    deposito_id = serializers.IntegerField(required=False)
    def validate(self, data): return data

class StockImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    taller_id = serializers.IntegerField(min_value=1)
    # Permite ajustar nombres de columnas si vienen distintos
    fields_map = serializers.DictField(
        child=serializers.CharField(),
        required=False
    )
    # Cómo aplicar la cantidad: "set" (por defecto) o "sum"
    mode = serializers.ChoiceField(
        choices=("set", "sum"),
        required=False,
        default="set"
    )


class CatalogoImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    fields_map = serializers.DictField(child=serializers.CharField(), required=False)
    default_estado = serializers.ChoiceField(choices=("ACTIVO", "INACTIVO"), required=False, default="ACTIVO")
    mode = serializers.ChoiceField(choices=("upsert", "create-only", "update-only"), required=False, default="upsert")


class DepositoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposito
        fields = ("id", "nombre", "taller_id")