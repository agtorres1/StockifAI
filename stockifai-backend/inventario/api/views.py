from django.db.models.expressions import When, Case, Value
from django.db.models.fields import IntegerField
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from datetime import date, timedelta, datetime, time
from .serializers import MovimientosImportSerializer, StockImportSerializer, CatalogoImportSerializer, \
    DepositoSerializer, AlertaSerializer
from ..models import Deposito, Movimiento, Alerta
from ..services._helpers import calcular_mos, compute_trend_line, get_month_ranges, batch_calculate_demand, MESES_ABREV, \
    get_historical_demand
from ..services.actualizar_alertas import actualizar_alertas_para_repuestos
from ..services.import_catalogo import importar_catalogo
from ..services.import_movimientos import importar_movimientos
from AI.services.forecast_pipeline import ejecutar_forecast_pipeline_por_taller, ejecutar_forecast_talleres
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union, Dict, Any
from ..services.import_stock import importar_stock
from django.db.models import Sum, Q, Prefetch, Count
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
        if resultado.get("repuestos_afectados_ids"):
            actualizar_alertas_para_repuestos(resultado["repuestos_afectados_ids"])
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


class AlertsListView(APIView):
    pagination_class = _StockPagination  # O el nombre de tu clase de paginación

    def get(self, request, taller_id: int):
        summary_mode = request.query_params.get("summary") == "1"

        active_alerts_qs = Alerta.objects.filter(
            repuesto_taller__taller_id=taller_id,
            estado__in=[Alerta.EstadoAlerta.NUEVA, Alerta.EstadoAlerta.VISTA]
        )

        if summary_mode:
            # CAMPANITA
            counts = active_alerts_qs.values('nivel').annotate(total=Count('id'))
            alert_counts = {
                Alerta.NivelAlerta.CRITICO: 0, Alerta.NivelAlerta.MEDIO: 0,
                Alerta.NivelAlerta.ADVERTENCIA: 0, Alerta.NivelAlerta.INFORMATIVO: 0
            }
            for item in counts:
                if item['nivel'] in alert_counts:
                    alert_counts[item['nivel']] = item['total']
            total_urgente = alert_counts[Alerta.NivelAlerta.CRITICO] + alert_counts[Alerta.NivelAlerta.MEDIO]
            alert_counts["TOTAL_URGENTE"] = total_urgente
            return Response(alert_counts)
        else:
            niveles_param = request.query_params.get('niveles')
            if niveles_param:
                lista_de_niveles = [nivel.strip().upper() for nivel in niveles_param.split(',')]
                active_alerts_qs = active_alerts_qs.filter(nivel__in=lista_de_niveles)
            ordered_alerts = (
                active_alerts_qs
                .annotate(
                    estado_prio=Case(
                        When(estado=Alerta.EstadoAlerta.NUEVA, then=Value(0)),
                        When(estado=Alerta.EstadoAlerta.VISTA, then=Value(1)),
                        default=Value(9),
                        output_field=IntegerField(),
                    )
                )
                .select_related('repuesto_taller__repuesto')
                .order_by('estado_prio', '-fecha_creacion', '-id')
            )
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(ordered_alerts, request, view=self)
            if page is not None:
                serializer = AlertaSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = AlertaSerializer(ordered_alerts, many=True)
            return Response(serializer.data)

class DismissAlertView(APIView):
    """
    POST /alertas/<alerta_id>/dismiss/

    Cambia el estado de una alerta a 'DESCARTADA' para ocultarla de la vista principal.
    """
    def post(self, request, alerta_id: int):
        # Buscamos la alerta. Si no existe, devuelve un error 404.
        alerta = get_object_or_404(Alerta, id=alerta_id)

        alerta.estado = Alerta.EstadoAlerta.DESCARTADA
        #alerta.descartada_por = request.user # Asigna el usuario que la descartó
        alerta.save(update_fields=['estado', 'descartada_por'])

        return Response(
            {"status": "Alerta descartada correctamente"},
            status=status.HTTP_200_OK
        )


class MarkAsSeenAlertView(APIView):
    """
    POST /alertas/<alerta_id>/mark-as-seen/

    Cambia el estado de una alerta de 'NUEVA' a 'VISTA'.
    """

    def post(self, request, alerta_id: int):
        # Buscamos la alerta. Si no existe, devuelve un error 404.
        alerta = get_object_or_404(Alerta, pk=alerta_id)

        # Opcional: Verificación de permisos
        # if alerta.repuesto_taller.taller != request.user.taller:
        #     return Response({"detail": "Permiso denegado."}, status=status.HTTP_403_FORBIDDEN)

        # Solo cambiamos el estado si es 'NUEVA' para evitar acciones innecesarias
        if alerta.estado == Alerta.EstadoAlerta.NUEVA:
            alerta.estado = Alerta.EstadoAlerta.VISTA
            alerta.save(update_fields=['estado'])

        return Response(
            {"status": "Alerta marcada como vista"},
            status=status.HTTP_200_OK
        )