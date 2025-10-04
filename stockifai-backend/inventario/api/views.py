from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from datetime import datetime, timedelta, date
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

class ConsultarForecastingListView(APIView):
    """
    GET /talleres/<taller_id>/forecasting

    Muestra una lista paginada de todos los repuestos del taller,
    incluyendo Stock Total, MOS y las 4 predicciones de demanda.
    """
    pagination_class = _StockPagination # Reutiliza la paginación

    def get(self, request, taller_id: int):
        # Filtros de búsqueda (similares a ConsultarStockView si es necesario)
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
            # Ordenamos por MOS (ascendente: peor cobertura primero)
            # Esto requiere cálculo de MOS. Simplificaremos ordenando por un campo de la DB
            # o permitiremos solo los órdenes que no requieran cálculo complejo en DB.
            # Aquí ordenamos por número de pieza por defecto, se puede ordenar en el frontend
            rt_qs = rt_qs.order_by("repuesto__numero_pieza")
        elif ordering in ("numero_pieza", "-numero_pieza"):
            rt_qs = rt_qs.order_by(ordering.replace("numero_pieza", "repuesto__numero_pieza"))
        else:
            rt_qs = rt_qs.order_by("repuesto__numero_pieza")

        # 5. Paginación
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rt_qs, request)

        # 6. Serialización y Cálculo de MOS (MOS se calcula en Python)
        payload = []
        for rt in page:
            stock_total = Decimal(rt.stock_total or 0)
            forecast_semanas = [
                Decimal(rt.pred_1 or 0),
                Decimal(rt.pred_2 or 0),
                Decimal(rt.pred_3 or 0),
                Decimal(rt.pred_4 or 0),
            ]

            mos_en_semanas = calcular_mos(stock_total, forecast_semanas)

            item = {
                # Información base del repuesto (usamos el Serializer existente)
                "repuesto_taller": RepuestoTallerSerializer(rt).data,
                "stock_total": rt.stock_total or 0,
                # Datos de MOS y predicción para la tabla
                "mos_en_semanas": float(mos_en_semanas) if mos_en_semanas else None,
                "pred_1": float(rt.pred_1 or 0),
                "pred_2": float(rt.pred_2 or 0),
                "pred_3": float(rt.pred_3 or 0),
                "pred_4": float(rt.pred_4 or 0),
            }
            payload.append(item)

        return paginator.get_paginated_response(payload)

class DetalleForecastingView(APIView):
    """
    GET /talleres/<taller_id>/repuestos/<repuesto_taller_id>/forecasting

    Genera los datos estructurados para los gráficos de demanda y rotación,
    usando los datos de predicción (pred_1 a pred_4) y el stock en tiempo real.

    NOTA: Las constantes NUM_HISTORICO, NUM_FORECAST_GRAFICO y CONFIDENCE_PCT
    deben matchear con las variables que usa tu componente Angular.
    """

    # Parámetros para matchear las variables del frontend de Angular
    NUM_HISTORICO = 16
    NUM_FORECAST_GRAFICO = 6
    CONFIDENCE_PCT = 0.04

    def get(self, request, taller_id: int, repuesto_taller_id: int):
        # 1. Recuperar el RepuestoTaller y anotar el stock total
        try:
            # Anotamos stock_total usando el mismo filtro que en ConsultarStockView
            rt_qs = (
                RepuestoTaller.objects
                .filter(id_repuesto_taller=repuesto_taller_id, taller_id=taller_id)
                .select_related('repuesto', 'repuesto__categoria')  # Asegurar que la serialización funcione
                .annotate(stock_total=Sum("stocks__cantidad", filter=Q(stocks__deposito__taller_id=taller_id)))
            )
            rt = rt_qs.first()

            if not rt:
                raise RepuestoTaller.DoesNotExist

        except RepuestoTaller.DoesNotExist:
            return Response(
                {"detail": "RepuestoTaller no encontrado o no pertenece al taller."},
                status=status.HTTP_404_NOT_FOUND
            )

        # --- PREPARACIÓN DE DATOS BASE ---

        stock_actual = float(rt.stock_total or 0)

        # 1. Obtener Forecast de 6 semanas (pred_1 a pred_4 de DB, las otras 2 se simulan/extrapolan)
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

        # 2. Histórico (16 semanas) - Usa la simulación temporal
        historico_data: List[float] = get_historical_demand(rt.id_repuesto_taller, self.NUM_HISTORICO)

        # 3. Construir la Serie Completa (Histórico + Proyección) para la Tendencia
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

        grafico_demanda_payload = {
            "historico": historico_chart_data,
            "forecastMedia": forecast_media_chart_data,
            "forecastLower": forecast_lower_data,
            "forecastUpper": forecast_upper_data,
            "tendencia": tendencia_data,
            "splitIndex": self.NUM_HISTORICO,
        }

        # --- GRAFICO 2: STOCK PROYECTADO VS DEMANDA (Línea de Cobertura) ---

        num_semanas_cobertura = 4

        # Usamos las 4 predicciones reales de la DB para la demanda
        demanda_proyectada_cobertura = predicciones_db

        # 1. Calcular la serie de Stock Proyectado (Stock decreciente)
        stock_restante = stock_actual
        # Incluye el stock inicial (semana 0) y el stock al final de cada semana
        stock_proyectado = [stock_actual]

        for demanda in demanda_proyectada_cobertura:
            stock_restante -= demanda
            # El stock nunca es negativo en la visualización de la línea
            stock_proyectado.append(max(0, stock_restante))

            # Añadir un punto inicial cero a la demanda para que la serie matchee la longitud
        # Las barras de demanda se verán solo a partir de la semana 1 de proyección.
        demanda_proyectada_cobertura.insert(0, 0.0)

        grafico_cobertura_payload = {
            "stock_proyectado": stock_proyectado,
            # La demanda proyectada tiene N+1 puntos (incluye el punto 0 inicial)
            "demanda_proyectada": demanda_proyectada_cobertura,
            # Las etiquetas deben incluir la semana actual (Sem Actual)
            "labels": ["Actual"] + [f'Sem {self.NUM_HISTORICO + i + 1}' for i in range(num_semanas_cobertura)]
        }

        # --- RESPUESTA FINAL (JSON principal) ---

        payload = {
            # Serializamos la información básica del repuesto usando tu Serializer existente
            "repuesto_info": RepuestoTallerSerializer(rt).data,
            "stock_actual": stock_actual,
            "dias_de_stock_restantes": dias_de_stock_restantes,

            "grafico_demanda": grafico_demanda_payload,
            "grafico_cobertura": grafico_cobertura_payload,  # Clave del Gráfico 2
        }

        return Response(payload)


def get_historical_demand(repuesto_taller_id: int, num_weeks: int = 16) -> List[float]:
    """
    Calcula la demanda histórica (salidas de inventario) para las últimas 'num_weeks'.

    Esta función asume que:
    1. La demanda es igual a la suma de los movimientos de salida (tipo='SALIDA').
    2. Los movimientos se agrupan por semana (TruncWeek).
    3. Retorna 16 valores, rellenando con 0 donde no hubo movimientos.
    """

    # 1. Definir el rango de fechas (últimas N semanas completas)
    # Encuentra la fecha de hoy.
    today = date.today()
    # Encuentra la fecha de inicio de la semana actual (Lunes)
    start_of_current_week = today - timedelta(days=today.weekday())

    # El rango debe ir desde N semanas antes hasta el inicio de la semana actual.
    start_date = start_of_current_week - timedelta(weeks=num_weeks)

    # 2. Consultar y agregar los movimientos de SALIDA
    # Filtra por el repuesto_taller, dentro del rango de fechas, y por tipo SALIDA.
    demand_data = Movimiento.objects.filter(
        stock_por_deposito__repuesto_taller_id=repuesto_taller_id,
        tipo='EGRESO',
        fecha__gte=start_date,
        fecha__lt=start_of_current_week  # Excluye la semana actual
    ).annotate(
        # Agrupa por el inicio de la semana
        week=TruncWeek('fecha')
    ).values('week').annotate(
        # Suma las cantidades por semana
        demanda_semanal=Sum('cantidad')
    ).order_by('week')

    # 3. Formatear y rellenar con ceros

    # Crea un diccionario para fácil acceso por fecha de inicio de semana
    demand_map = {item['week'].date(): float(item['demanda_semanal']) for item in demand_data}

    final_historical_data: List[float] = []
    current_week_start = start_date

    # Itera sobre las N semanas esperadas
    for _ in range(num_weeks):
        demand_value = demand_map.get(current_week_start, 0.0)
        final_historical_data.append(demand_value)

        # Mueve a la siguiente semana
        current_week_start += timedelta(weeks=1)

    return final_historical_data


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
