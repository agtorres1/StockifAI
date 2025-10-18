from rest_framework import serializers

from catalogo.models import Repuesto, Categoria, Marca
from inventario.models import Deposito, Movimiento, Alerta
from catalogo.models import RepuestoTaller
from user.models import Grupo, Taller

class MovimientosImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    fields_map = serializers.JSONField(required=False)
    taller_id = serializers.IntegerField()
    deposito_nombre = serializers.CharField(required=False)
    deposito_id = serializers.IntegerField(required=False)
    def validate(seslf, data): return data

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
        fields = ["id", "nombre", "taller_id"]


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion"]


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ["id", "nombre"]


class RepuestoSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    marca = MarcaSerializer(read_only=True)

    class Meta:
        model = Repuesto
        fields = ["numero_pieza", "descripcion", "marca", "categoria", "estado"]


class MovimientosSerializer(serializers.ModelSerializer):
    deposito = DepositoSerializer(source="stock_por_deposito.deposito", read_only=True)
    repuesto = RepuestoSerializer(source="stock_por_deposito.repuesto_taller.repuesto", read_only=True)

    class Meta:
        model = Movimiento
        fields = ["id", "fecha", "tipo", "cantidad", "externo_id", "documento", "deposito", "repuesto"]

class TallerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taller
        fields = ["id", "nombre"]

class RepuestoTallerSerializer(serializers.ModelSerializer):
    repuesto = RepuestoSerializer(read_only=True)
    taller = TallerSerializer(read_only=True)
    cantidad_minima = serializers.SerializerMethodField()

    class Meta:
        model = RepuestoTaller
        fields = [
            "id_repuesto_taller",
            "repuesto",
            "taller",
            "precio",
            "costo",
            "original",
            "pred_1",
            "pred_2",
            "pred_3",
            "pred_4",
            "cantidad_minima",
            "frecuencia"
        ]

    def get_cantidad_minima(self, obj):
        # Por defecto, igual a pred_1 si existe
        return obj.pred_1

class StockDepositoDetalleSerializer(serializers.Serializer):
    deposito = DepositoSerializer()
    cantidad = serializers.IntegerField()

class RepuestoStockSerializer(serializers.Serializer):
    repuesto_taller = RepuestoTallerSerializer()
    stock_total = serializers.IntegerField()
    depositos = StockDepositoDetalleSerializer(many=True)


class GrupoResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField(allow_blank=True)
    grupo_padre_id = serializers.IntegerField(allow_null=True)
    es_subgrupo = serializers.BooleanField()


class TallerConStockSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    direccion = serializers.CharField(allow_blank=True)
    direccion_normalizada = serializers.CharField(allow_blank=True, required=False)
    telefono = serializers.CharField(allow_blank=True, required=False)
    telefono_e164 = serializers.CharField(allow_blank=True, required=False)
    email = serializers.CharField(allow_blank=True, required=False)
    latitud = serializers.FloatField(allow_null=True)
    longitud = serializers.FloatField(allow_null=True)
    cantidad = serializers.IntegerField()
    distancia_km = serializers.FloatField(allow_null=True, required=False)
    grupos = GrupoResumenSerializer(many=True)

class AlertaSerializer(serializers.ModelSerializer):
    """
    Serializador principal para el modelo Alerta.
    """
    repuesto_taller = RepuestoTallerSerializer(read_only=True)

    class Meta:
        model = Alerta
        fields = [
            'id',
            'repuesto_taller',
            'nivel',
            'codigo',
            'mensaje',
            'estado',
            'fecha_creacion',
            'datos_snapshot' # El snapshot es clave para el contexto
        ]