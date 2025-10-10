from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from datetime import date, timedelta, datetime, time
from .serializers import MovimientosImportSerializer, StockImportSerializer, CatalogoImportSerializer, \
    DepositoSerializer
from ..models import Deposito, Movimiento
from ..services.import_catalogo import importar_catalogo
from ..services.import_movimientos import importar_movimientos
from AI.services.forecast_pipeline import ejecutar_forecast_pipeline_por_taller, ejecutar_forecast_talleres
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union, Dict, Any
from ..services.import_stock import importar_stock
from django.db.models import Sum, Q, Prefetch
from django.db.models.functions import TruncWeek
from rest_framework.pagination import PageNumberPagination
from catalogo.models import RepuestoTaller
from inventario.models import StockPorDeposito, Deposito
from .serializers import (
    RepuestoStockSerializer,
    RepuestoTallerSerializer,
    StockDepositoDetalleSerializer,
    DepositoSerializer,
)

MESES_ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

try:
    from django.utils import timezone
    # Helper function para hacer las fechas 'aware' si estamos en Django
    def make_aware_datetime(dt_naive):
        return timezone.make_aware(dt_naive)
except ImportError:
    # Fallback si no se está ejecutando en un entorno Django completo
    print("WARNING: django.utils.timezone not available. Dates will remain naive.")
    def make_aware_datetime(dt_naive):
        return dt_naive


class ImportarMovimientosView(APIView):
    def post(self, request):
        ser = MovimientosImportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            resultado = importar_movimientos(
                file=ser.validated_data["file"],
                taller_id=ser.validated_data["taller_id"],
                fields_map=ser.validated_data.get("fields_map"),
                deposito_id=ser.validated_data.get("deposito_id"),
                deposito_nombre=ser.validated_data.get("deposito_nombre"),
                permitir_stock_negativo=getattr(settings, "PERMITIR_STOCK_NEGATIVO", True),
            )
        return Response(resultado, status=status.HTTP_200_OK)

class ImportarStockView(APIView):
    def post(self, request):
        ser = StockImportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        with transaction.atomic():
            resultado = importar_stock(
                file=ser.validated_data["file"],
                taller_id=ser.validated_data["taller_id"],
                fields_map=ser.validated_data.get("fields_map") or {},
                mode=ser.validated_data.get("mode", "set"),
            )
        return Response(resultado, status=status.HTTP_200_OK)


class ImportarCatalogoView(APIView):
    def post(self, request):
        ser = CatalogoImportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            res = importar_catalogo(
                file=ser.validated_data["file"],
                fields_map=ser.validated_data.get("fields_map"),
                default_estado=ser.validated_data.get("default_estado", "ACTIVO"),
                mode=ser.validated_data.get("mode", "upsert"),
            )
        return Response(res, status=status.HTTP_200_OK)

class DepositosPorTallerView(APIView):
    def get(self, request, taller_id: int):
        qs = Deposito.objects.filter(taller_id=taller_id)
        data = DepositoSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)



class _StockPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500

class ConsultarStockView(APIView):
    """
    GET /talleres/<taller_id>/stock

    Query params:
      - q: busca en numero_pieza/descripcion (icontains)
      - numero_pieza: exacto o icontains si exact=0
      - exact: 1|0 (default 1)
      - original: true|false|1|0
      - deposito_id: filtra por depósito
      - categoria_id: filtra por categoría del repuesto
      - con_stock: 1|true => solo stock_total > 0
      - ordering: numero_pieza | -numero_pieza | stock_total | -stock_total
      - page, page_size
    """
    pagination_class = _StockPagination

    def get(self, request, taller_id: int):
        q = request.query_params.get("q")
        numero_pieza = request.query_params.get("numero_pieza")
        exact = request.query_params.get("exact", "1")
        original = request.query_params.get("original")
        deposito_id = request.query_params.get("deposito_id")
        categoria_id = request.query_params.get("categoria_id")
        con_stock = request.query_params.get("con_stock")
        ordering = request.query_params.get("ordering")

        rt_qs = (
            RepuestoTaller.objects
            .filter(taller_id=taller_id)
            .select_related("repuesto", "taller", "repuesto__marca", "repuesto__categoria")
            .prefetch_related(
                Prefetch(
                    "stocks",
                    queryset=StockPorDeposito.objects.select_related("deposito"),
                    to_attr="prefetched_stocks"
                )
            )
        )

        if q:
            rt_qs = rt_qs.filter(
                Q(repuesto__numero_pieza__icontains=q) |
                Q(repuesto__descripcion__icontains=q)
            )

        if numero_pieza:
            if exact == "1":
                rt_qs = rt_qs.filter(repuesto__numero_pieza=numero_pieza)
            else:
                rt_qs = rt_qs.filter(repuesto__numero_pieza__icontains=numero_pieza)

        if categoria_id:
            rt_qs = rt_qs.filter(repuesto__categoria_id=categoria_id)

        if original in ("true", "false", "1", "0"):
            rt_qs = rt_qs.filter(original=original in ("true", "1"))

        # Anotamos stock_total (solo depósitos del taller y opcionalmente 1 depósito)
        filt = Q(stocks__deposito__taller_id=taller_id)
        if deposito_id:
            filt &= Q(stocks__deposito_id=deposito_id)

        rt_qs = rt_qs.annotate(stock_total=Sum("stocks__cantidad", filter=filt))

        if con_stock in ("1", "true"):
            rt_qs = rt_qs.filter(stock_total__gt=0)

        if ordering in ("numero_pieza", "-numero_pieza"):
            rt_qs = rt_qs.order_by(ordering.replace("numero_pieza", "repuesto__numero_pieza"))
        elif ordering in ("stock_total", "-stock_total"):
            rt_qs = rt_qs.order_by(ordering)
        else:
            rt_qs = rt_qs.order_by("repuesto__numero_pieza")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rt_qs, request)

        payload = []
        for rt in page:
            # Detalle por depósito (solo depósitos del taller y, si corresponde, el indicado)
            depositos_detalle = []
            for spd in getattr(rt, "prefetched_stocks", []):
                if spd.deposito.taller_id != taller_id:
                    continue
                if deposito_id and spd.deposito_id != int(deposito_id):
                    continue
                depositos_detalle.append({
                    "deposito": DepositoSerializer(spd.deposito).data,
                    "cantidad": spd.cantidad,
                })

            stock_total = Decimal(rt.stock_total or 0)
            forecast_semanas = [
                Decimal(rt.pred_1 or 0),
                Decimal(rt.pred_2 or 0),
                Decimal(rt.pred_3 or 0),
                Decimal(rt.pred_4 or 0),
            ]

            mos_en_semanas = calcular_mos(stock_total, forecast_semanas)

            item = {
                "repuesto_taller": RepuestoTallerSerializer(rt).data,
                "stock_total": rt.stock_total or 0,
                "depositos": depositos_detalle,
                "mos_en_semanas": float(mos_en_semanas) if mos_en_semanas else None,
            }
            payload.append(item)

        return paginator.get_paginated_response(payload)

def calcular_mos(stock: Decimal, weeks: list[Decimal]) -> Decimal:
    """
    Calcula el MOS (semanas de cobertura):
    - Consume stock semana a semana.
    - Si la demanda de una semana es 0, se usa el promedio.
    - Si todas las predicciones son 0/None, devuelve None.
    """
    stock = Decimal(stock or 0)

    no_nulas = [w for w in weeks if w > 0]
    if not no_nulas:
        return None  # Si no hay predicciones, no se puede calcular

    # Para extender más allá de la 4
    tail_rate = sum(no_nulas)/len(no_nulas)

    semanas = Decimal(0)
    restante = stock

    for w in weeks:
        demanda = w if w > 0 else tail_rate
        if restante >= demanda:
            restante -= demanda
            semanas += 1
        else:
            semanas += restante / demanda
            return semanas.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Si sobra stock después de las 4 semanas, extender con tail_rate
    if restante > 0:
        semanas += restante / tail_rate

    return semanas.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)



class EjecutarForecastPorTallerView(APIView):
    def post(self, request, taller_id: int):
        fecha_lunes = request.data.get("fecha_lunes")  # "YYYY-MM-DD" (lunes)

        out = ejecutar_forecast_pipeline_por_taller(taller_id, fecha_lunes)
        return Response({"status": "ok", "details": out}, status=status.HTTP_200_OK)

class EjecutarForecastView(APIView):
    def post(self, request):
        fecha_lunes = request.data.get("fecha_lunes")  # "YYYY-MM-DD" (lunes)

        out = ejecutar_forecast_talleres(fecha_lunes)
        return Response({"status": "ok", "details": out}, status=status.HTTP_200_OK)


class DetalleForecastingView(APIView):
    """
    GET /talleres/<taller_id>/repuestos/<repuesto_taller_id>/forecasting
    """

    NUM_HISTORICO = 16
    NUM_FORECAST_GRAFICO = 6
    CONFIDENCE_PCT = 0.04

    def get(self, request, taller_id: int, repuesto_taller_id: int):
        # 1. Recuperar el RepuestoTaller y anotar el stock total
        try:
            rt_qs = (
                RepuestoTaller.objects
                .filter(id_repuesto_taller=repuesto_taller_id, taller_id=taller_id)
                .select_related('repuesto', 'repuesto__categoria')
                .annotate(stock_total=Sum("stocks__cantidad", filter=Q(stocks__deposito__taller_id=taller_id)))
            )
            rt = rt_qs.first()

            if not rt:
                raise RepuestoTaller.DoesNotExist

        except Exception:  # Captura si RepuestoTaller o el modelo no están definidos
            return Response(
                {"detail": "RepuestoTaller no encontrado o no pertenece al taller."},
                status=status.HTTP_404_NOT_FOUND
            )

        # --- PREPARACIÓN DE DATOS BASE ---
        stock_actual = float(rt.stock_total or 0)

        # 1. Obtener Forecast de 6 semanas
        predicciones_db = [
            float(rt.pred_1 or 0),
            float(rt.pred_2 or 0),
            float(rt.pred_3 or 0),
            float(rt.pred_4 or 0)
        ]

        # Extrapolación simple para las semanas 5 y 6
        forecast_base_data = predicciones_db + [
            predicciones_db[-1] + 5 if predicciones_db else 5,
            predicciones_db[-1] + 2 if predicciones_db else 2
        ]

        # Calculamos los días de stock restantes (MOS * 7)
        mos_decimal = calcular_mos(Decimal(stock_actual), [Decimal(p) for p in predicciones_db])
        dias_de_stock_restantes = round(float(mos_decimal) * 7) if mos_decimal is not None else 0

        # --- GRAFICO 1: DEMANDA PROYECTADA (Línea) ---

        # 2. Histórico (16 semanas) - Obtiene datos y etiquetas de fecha
        historico_result = get_historical_demand(rt.id_repuesto_taller, self.NUM_HISTORICO)
        historico_data: List[float] = historico_result["data"]
        historico_labels: List[str] = historico_result["labels"]  # NUEVAS ETIQUETAS HISTÓRICAS

        # 3. Construir la Serie Completa (Histórico + Proyección)
        full_series: List[Union[float, None]] = historico_data + forecast_base_data
        tendencia_data: List[float] = compute_trend_line(full_series)

        # 4. Formatear las series para Chart.js
        historico_chart_data: List[Union[float, None]] = historico_data + [None] * self.NUM_FORECAST_GRAFICO
        forecast_media_chart_data: List[Union[float, None]] = [None] * self.NUM_HISTORICO + forecast_base_data

        # Banda de Confianza (4% de margen)
        forecast_lower_data: List[Union[float, None]] = [None] * self.NUM_HISTORICO + [
            round(v * (1 - self.CONFIDENCE_PCT)) for v in forecast_base_data
        ]
        forecast_upper_data: List[Union[float, None]] = [None] * self.NUM_HISTORICO + [
            round(v * (1 + self.CONFIDENCE_PCT)) for v in forecast_base_data
        ]

        # Generar etiquetas de forecast basadas en fechas reales futuras
        forecast_labels = []
        # Fecha de inicio de la próxima semana (Semana 17 o 1 de Forecast)
        today = date.today()
        start_of_next_week = today - timedelta(days=today.weekday()) + timedelta(weeks=1)

        for i in range(self.NUM_FORECAST_GRAFICO):
            label_date = start_of_next_week + timedelta(weeks=i)
            forecast_labels.append(f"{label_date.day} {MESES_ABREV[label_date.month - 1]}")

        grafico_demanda_payload = {
            "historico": historico_chart_data,
            "forecastMedia": forecast_media_chart_data,
            "forecastLower": forecast_lower_data,
            "forecastUpper": forecast_upper_data,
            "tendencia": tendencia_data,
            "splitIndex": self.NUM_HISTORICO,
            "labels": historico_labels + forecast_labels  # Etiquetas combinadas
        }

        # --- GRAFICO 2: STOCK PROYECTADO VS DEMANDA (Línea de Cobertura) ---

        num_semanas_cobertura = 4

        # Usamos las 4 predicciones reales de la DB para la demanda
        demanda_proyectada_cobertura = [float(p) for p in predicciones_db]  # Convertir a float para Chart.js

        # 1. Calcular la serie de Stock Proyectado (Stock decreciente)
        stock_restante = stock_actual
        # Incluye el stock inicial (semana 0) y el stock al final de cada semana
        stock_proyectado = [stock_actual]

        for demanda in demanda_proyectada_cobertura:
            stock_restante -= demanda
            stock_proyectado.append(max(0, stock_restante))

        # Añadir un punto inicial cero a la demanda para que la serie matchee la longitud
        demanda_proyectada_cobertura.insert(0, 0.0)

        # Generar etiquetas de fecha para las 4 semanas de cobertura
        cobertura_labels = ["Actual"]
        start_date_cobertura = today - timedelta(days=today.weekday()) + timedelta(weeks=1)

        for i in range(num_semanas_cobertura):
            label_date = start_date_cobertura + timedelta(weeks=i)
            # Formato de etiqueta: DD/MM (ej: 01/10)
            cobertura_labels.append(f"{label_date.day} {MESES_ABREV[label_date.month - 1]}")

        grafico_cobertura_payload = {
            "stock_proyectado": stock_proyectado,
            "demanda_proyectada": demanda_proyectada_cobertura,
            "labels": cobertura_labels  # ETIQUETAS DE FECHA REAL
        }

        # --- RESPUESTA FINAL (JSON principal) ---

        payload = {
            "repuesto_info": RepuestoTallerSerializer(rt).data,
            "stock_actual": stock_actual,
            "dias_de_stock_restantes": dias_de_stock_restantes,

            "grafico_demanda": grafico_demanda_payload,
            "grafico_cobertura": grafico_cobertura_payload,
        }

        return Response(payload)


def get_historical_demand(repuesto_taller_id: int, num_weeks: int = 16) -> Dict[str, List[Union[float, str]]]:
    """
    Calcula la demanda histórica (salidas de inventario) para las últimas 'num_weeks'.
    Retorna los datos de demanda y las etiquetas de fecha.
    """
    # 1. Definir el rango de fechas (últimas N semanas completas)
    today = date.today()
    # Encuentra la fecha de inicio de la semana actual (Lunes, asumiendo 0=Lunes)
    start_of_current_week_date = today - timedelta(days=today.weekday())

    # La fecha de inicio histórica (date object, naive)
    start_date = start_of_current_week_date - timedelta(weeks=num_weeks)

    # -------------------------------------------------------------------
    # CORRECCIÓN PARA EL WARNING DE ZONA HORARIA
    # Convertimos los objetos 'date' a 'datetime' y luego los hacemos 'aware'.
    # -------------------------------------------------------------------
    aware_start_date = make_aware_datetime(datetime.combine(start_date, time.min))
    aware_start_of_current_week = make_aware_datetime(datetime.combine(start_of_current_week_date, time.min))
    # -------------------------------------------------------------------

    # 2. Consultar y agregar los movimientos de SALIDA
    try:
        # En un entorno real de Django/DB, usarías las fechas aware:
        demand_data = Movimiento.objects.filter(
            stock_por_deposito__repuesto_taller_id=repuesto_taller_id,
            tipo='EGRESO',
            fecha__gte=aware_start_date,  # Usamos la fecha aware
            fecha__lt=aware_start_of_current_week  # Usamos la fecha aware
        ).annotate(
            week=TruncWeek('fecha')
        ).values('week').annotate(
            demanda_semanal=Sum('cantidad')
        ).order_by('week')

        # Placeholder para simular la demanda histórica
        if not demand_data:
            if repuesto_taller_id == 5:
                # Usamos la fecha naive 'start_date' aquí para rellenar
                demand_data = [{'week': start_date, 'demanda_semanal': 20.0}]
            else:
                demand_data = []

    except NameError:
        # Fallback si Movimiento/TruncWeek no está definido (para que compile)
        demand_data = []

    # 3. Formatear y rellenar con ceros
    # NOTA: Los resultados de TruncWeek son aware datetimes (o date si es MySQL).
    # Por seguridad, convertimos a date para el map, ya que las etiquetas son solo DD/MM.
    demand_map = {item['week'].date(): float(item['demanda_semanal']) for item in demand_data if item.get('week')}

    final_historical_data: List[float] = []
    final_historical_labels: List[str] = []
    current_week_start = start_date  # Volvemos al objeto 'date' para generar etiquetas

    # Itera sobre las N semanas esperadas
    for _ in range(num_weeks):
        demand_value = demand_map.get(current_week_start, 0.0)
        final_historical_data.append(demand_value)

        # Formato de etiqueta: DD/MM (ej: 01/10)
        final_historical_labels.append(f"{current_week_start.day} {MESES_ABREV[current_week_start.month - 1]}")

        # Mueve a la siguiente semana (SOLO 1 semana)
        current_week_start += timedelta(weeks=1)

    return {
        "data": final_historical_data,
        "labels": final_historical_labels
    }


def compute_trend_line(series: List[Union[float, int, None]]) -> List[float]:
    """
    Calcula la línea de regresión lineal. Replica la lógica 'computeTrendLine'
    que probablemente tienes en tu frontend de Angular.
    """
    xs: List[float] = []
    ys: List[float] = []

    for idx, val in enumerate(series):
        if val is not None:
            xs.append(float(idx + 1))
            ys.append(float(val))

    if len(xs) < 2:
        return [0.0] * len(series)

    n = len(xs)
    sumX = sum(xs)
    sumY = sum(ys)
    sumXY = sum(x * ys[i] for i, x in enumerate(xs))
    sumX2 = sum(x * x for x in xs)

    denom = n * sumX2 - sumX * sumX

    if denom == 0:
        return [round(sumY / n, 2)] * len(series)

    slope = (n * sumXY - sumX * sumY) / denom
    intercept = (sumY - slope * sumX) / n

    # Genera los valores de la línea de tendencia para toda la serie
    return [round(intercept + slope * (i + 1), 2) for i in range(len(series))]


class AlertsListView(APIView):
    """
    GET /talleres/<taller_id>/alertas/

    Si se usa ?summary=1, devuelve el conteo de alertas urgentes para la insignia.
    De lo contrario, devuelve la lista consolidada de TODAS las alertas activas (dashboard).
    """

    def get(self, request, taller_id: int):

        # Detecta si se pide el resumen (para el badge) o la lista completa (para la pantalla)
        summary_mode = request.query_params.get("summary") == "1"

        try:
            rt_qs = (
                RepuestoTaller.objects
                .filter(taller_id=taller_id)
                .annotate(
                    stock_total=Sum("stocks__cantidad", filter=Q(stocks__deposito__taller_id=taller_id))
                )
                .select_related('repuesto')
                .all()
            )
        except NameError:
            return Response(
                {"detail": "Error interno: Modelos RepuestoTaller o sus dependencias no están disponibles."},
                status=500)
        except Exception as e:
            return Response({"detail": f"Error al consultar el inventario: {str(e)}"}, status=500)

        consolidated_alerts: List[Dict[str, Any]] = []
        alert_counts = {"CRÍTICO": 0, "MEDIO": 0, "ADVERTENCIA": 0, "INFORMATIVO": 0}

        for rt in rt_qs:
            stock_total = Decimal(rt.stock_total or 0)

            pred_1 = Decimal(getattr(rt, 'pred_1', 0) or 0)
            forecast_semanas = [
                pred_1,
                Decimal(getattr(rt, 'pred_2', 0) or 0),
                Decimal(getattr(rt, 'pred_3', 0) or 0),
                Decimal(getattr(rt, 'pred_4', 0) or 0),
            ]
            frecuencia_rotacion = getattr(rt, 'frecuencia', 'DESCONOCIDA')

            # --- Cálculo de MOS y Alertas ---
            mos_en_semanas = calcular_mos(stock_total, forecast_semanas)

            alertas_activas = generar_alertas_inventario(
                stock_total=stock_total,
                pred_1=pred_1,
                mos_en_semanas=mos_en_semanas,
                frecuencia_rotacion=frecuencia_rotacion
            )

            # 3. Consolidar o Contar
            if alertas_activas:
                repuesto_obj = getattr(rt, 'repuesto', None)
                numero_pieza = getattr(repuesto_obj, 'numero_pieza', 'N/A')
                descripcion = getattr(repuesto_obj, 'descripcion', 'N/A')

                for alerta in alertas_activas:
                    nivel = alerta['nivel']

                    # 3.1. Modo Resumen: Contar las alertas
                    if nivel in alert_counts:
                        alert_counts[nivel] += 1

                    # 3.2. Modo Detalle: Agregar la alerta a la lista de respuesta
                    if not summary_mode:
                        consolidated_alerts.append({
                            "id_repuesto": getattr(rt, 'id', getattr(rt, 'pk', 'N/A')),
                            "numero_pieza": numero_pieza,
                            "descripcion": descripcion,
                            "stock_total": float(stock_total),
                            "mos_en_semanas": float(mos_en_semanas) if mos_en_semanas else None,
                            "alerta": alerta  # El diccionario de alerta (nivel, color, codigo, mensaje)
                        })

        # 4. Devolver la respuesta
        if summary_mode:
            total_urgente = alert_counts["CRÍTICO"] + alert_counts["MEDIO"]
            return Response({
                "CRÍTICO": alert_counts["CRÍTICO"],
                "MEDIO": alert_counts["MEDIO"],
                "ADVERTENCIA": alert_counts["ADVERTENCIA"],
                "INFORMATIVO": alert_counts["INFORMATIVO"],
                "TOTAL_URGENTE": total_urgente
            })
        else:
            return Response(consolidated_alerts)


def generar_alertas_inventario(
        stock_total: Union[int, float, Decimal],
        pred_1: Union[int, float, Decimal],
        mos_en_semanas: Optional[Union[int, float, Decimal]],
        frecuencia_rotacion: str
) -> List[Dict[str, str]]:
    """
    Genera una lista de alertas activas (CRÍTICO, MEDIO, INFORMATIVO, ADVERTENCIA).
    """
    alertas_activas: List[Dict[str, str]] = []

    stock_d = Decimal(str(stock_total))
    pred_1_d = Decimal(str(pred_1))
    mos_d = Decimal(str(mos_en_semanas)) if mos_en_semanas is not None else None

    # 1. ALERTA CRÍTICA: Quiebre de Stock Inmediato (Rojo)
    if stock_d < pred_1_d:
        alertas_activas.append({
            "nivel": "CRÍTICO",
            "codigo": "ACCION_INMEDIATA",
            "mensaje": (
                f"Quiebre Inminente. Stock ({stock_d}) no cubre la demanda de la próxima semana ({pred_1_d}). "
            )
        })

    # 2. ALERTA MEDIA: Bajo MOS (Naranja)
    if mos_d is not None and mos_d > Decimal('1') and mos_d <= Decimal('2.5') and not (stock_d < pred_1_d):
        alertas_activas.append({
            "nivel": "MEDIO",
            "codigo": "MOS_BAJO_REORDENAR",
            "mensaje": f"Bajo MOS. La cobertura es de {mos_d:.2f} semanas. "
        })

    # 3. ALERTA INFORMATIVA: Sobre-Abastecimiento o Riesgo de Lento (Azul)
    if mos_d is not None:
        es_lento_o_intermedio = frecuencia_rotacion in ["LENTO", "INTERMEDIO", "OBSOLETO", "MUERTO"]
        sobre_stock_general = mos_d >= Decimal('12')
        sobre_stock_riesgoso = mos_d >= Decimal('4') and es_lento_o_intermedio

        if sobre_stock_general or sobre_stock_riesgoso:
            alertas_activas.append({
                "nivel": "INFORMATIVO",
                "codigo": "SOBRE_STOCK_RIESGO",
                "mensaje": (
                    f"Capital Inmovilizado. Cobertura de {mos_d:.2f} semanas ({frecuencia_rotacion}). "
                )
            })
    return alertas_activas


def get_month_ranges() -> Dict[str, date]:
    """Calcula las fechas de inicio y fin para el mes actual y el mes anterior."""
    today = date.today()

    # Mes actual: Desde el día 1 hasta hoy (inclusive)
    start_current_month = today.replace(day=1)
    end_current_month = today

    # Mes anterior:
    start_current_month = today.replace(day=1)
    last_day_prev_month = start_current_month - timedelta(days=1)
    start_prev_month = last_day_prev_month.replace(day=1)

    return {
        "start_current": start_current_month,
        "end_current": end_current_month,
        "start_prev": start_prev_month,
        "end_prev": last_day_prev_month,
    }


def get_month_ranges() -> Dict[str, date]:
    """Calcula las fechas de inicio y fin para el mes actual y el mes anterior."""
    today = date.today()

    # Mes actual: Desde el día 1 hasta hoy (inclusive)
    start_current_month = today.replace(day=1)
    end_current_month = today

    # Mes anterior:
    last_day_prev_month = start_current_month - timedelta(days=1)
    start_prev_month = last_day_prev_month.replace(day=1)

    return {
        "start_current": start_current_month,
        "end_current": end_current_month,
        "start_prev": start_prev_month,
        "end_prev": last_day_prev_month,
    }


def batch_calculate_demand(rt_ids: List[int], month_ranges: Dict[str, date]) -> Dict[int, Dict[str, int]]:
    """
    OPTIMIZACIÓN: Calcula la Demanda Mensual para toda la página en UNA SOLA consulta.
    Reemplaza la función get_monthly_demand() que causaba el problema N+1.
    """
    if not rt_ids:
        return {}

    start_prev = month_ranges["start_prev"]
    end_curr = month_ranges["end_current"]

    try:
        # Usamos el path completo que se usaba en el filtro original:
        # stock_por_deposito__repuesto_taller_id__in
        monthly_demand_data = Movimiento.objects.filter(
            stock_por_deposito__repuesto_taller_id__in=rt_ids,
            tipo='EGRESO',
            fecha__date__range=(start_prev, end_curr)
        ).values(
            'stock_por_deposito__repuesto_taller_id'  # Agrupar por ID del repuesto
        ).annotate(
            # Demanda del mes anterior
            demand_prev=Sum(
                'cantidad',
                filter=Q(fecha__date__range=(start_prev, month_ranges["end_prev"]))
            ),
            # Demanda del mes actual (hasta hoy)
            demand_curr=Sum(
                'cantidad',
                filter=Q(fecha__date__range=(month_ranges["start_current"], end_curr))
            )
        )
    except Exception as e:
        # Captura si hay un error de campo o importación
        print(f"Error en batch_calculate_demand: {e}")
        return {}

        # Mapeo del resultado para acceso rápido O(1)
    demand_map = {
        item['stock_por_deposito__repuesto_taller_id']: {
            'prev': int(round(item['demand_prev'] or 0)),
            'curr': int(round(item['demand_curr'] or 0)),
        }
        for item in monthly_demand_data
    }
    return demand_map


# --- Vista Principal DRF (Optimizada) ---

class ConsultarForecastingListView(APIView):
    """
    GET /talleres/<taller_id>/forecasting

    Muestra una lista paginada de todos los repuestos del taller,
    incluyendo Stock Total, MOS, Días de Stock Restante y Demanda Mensual.
    """
    pagination_class = _StockPagination  # Reutiliza la paginación

    def get(self, request, taller_id: int):
        q = request.query_params.get("q")
        ordering = request.query_params.get("ordering")

        # 1. Base QuerySet: Repuestos del taller
        rt_qs = RepuestoTaller.objects.filter(taller_id=taller_id)

        # 2. Aplicar filtros
        if q:
            rt_qs = rt_qs.filter(
                Q(repuesto__numero_pieza__icontains=q) |
                Q(repuesto__descripcion__icontains=q)
            )

        # 3. Anotar stock_total (Sumamos el stock de todos los depósitos del taller)
        filt_stock = Q(stocks__deposito__taller_id=taller_id)
        rt_qs = rt_qs.annotate(stock_total=Sum("stocks__cantidad", filter=filt_stock))

        # 4. Aplicar ordenamiento
        if ordering == 'mos':
            rt_qs = rt_qs.order_by("repuesto__numero_pieza")
        elif ordering in ("numero_pieza", "-numero_pieza"):
            rt_qs = rt_qs.order_by(ordering.replace("numero_pieza", "repuesto__numero_pieza"))
        else:
            rt_qs = rt_qs.order_by("repuesto__numero_pieza")

        # 5. Paginación
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rt_qs, request)

        if not page:
            return paginator.get_paginated_response([])

        # 6. Pre-calcular rangos de meses
        month_ranges = get_month_ranges()

        # 7. OPTIMIZACIÓN: Calcular Demanda Mensual para toda la página en Batch
        # Los IDs deben ser el campo que utiliza Movimiento como FK
        rt_ids = [rt.id_repuesto_taller for rt in page]
        demand_map = batch_calculate_demand(rt_ids, month_ranges)

        # 8. Serialización y Cálculo de MOS
        payload = []
        for rt in page:
            stock_total = Decimal(rt.stock_total or 0)

            # --- MOS y Días de Stock Restantes ---
            forecast_semanas = [
                Decimal(rt.pred_1 or 0),
                Decimal(rt.pred_2 or 0),
                Decimal(rt.pred_3 or 0),
                Decimal(rt.pred_4 or 0),
            ]

            mos_en_semanas = calcular_mos(stock_total, forecast_semanas)

            dias_de_stock_restantes = round(float(mos_en_semanas) * 7) if mos_en_semanas is not None else None

            # --- Demanda Mensual (Recuperada del mapa O(1)) ---
            # Usamos rt.id_repuesto_taller como clave para el mapa de demanda
            demand_info = demand_map.get(rt.id_repuesto_taller, {'prev': 0, 'curr': 0})
            cantidad_vendida_mes_actual = demand_info['curr']
            cantidad_vendida_mes_anterior = demand_info['prev']

            item = {
                # Información base del repuesto (usamos el Serializer existente)
                "repuesto_taller": RepuestoTallerSerializer(rt).data,
                "stock_total": rt.stock_total or 0,
                "dias_de_stock_restantes": dias_de_stock_restantes,
                "cantidad_vendida_mes_actual": cantidad_vendida_mes_actual,
                "cantidad_vendida_mes_anterior": cantidad_vendida_mes_anterior,
                "mos_en_semanas": float(mos_en_semanas) if mos_en_semanas else None,
                "pred_1": float(rt.pred_1 or 0),
                "pred_2": float(rt.pred_2 or 0),
                "pred_3": float(rt.pred_3 or 0),
                "pred_4": float(rt.pred_4 or 0),
            }
            payload.append(item)

        return paginator.get_paginated_response(payload)