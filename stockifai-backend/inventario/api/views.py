from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.db import transaction
from .serializers import MovimientosImportSerializer, StockImportSerializer, CatalogoImportSerializer, \
    DepositoSerializer
from ..models import Deposito
from ..services.import_catalogo import importar_catalogo
from ..services.import_movimientos import importar_movimientos
from AI.services.forecast_pipeline import ejecutar_forecast_pipeline_por_taller, ejecutar_forecast_talleres
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP

from ..services.import_stock import importar_stock
from django.db.models import Sum, Q, Prefetch
from rest_framework.pagination import PageNumberPagination
from catalogo.models import RepuestoTaller
from inventario.models import StockPorDeposito, Deposito
from .serializers import (
    RepuestoStockSerializer,
    RepuestoTallerSerializer,
    StockDepositoDetalleSerializer,
    DepositoSerializer,
)


from rest_framework.decorators import action

from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta


from inventario.models import Movimiento, StockPorDeposito, ObjetivoKPI
from inventario.api.serializers import ObjetivoKPISerializer
from user.api.models.models import Taller, User


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


class KPIsViewSet(viewsets.ViewSet):

    def _get_objetivo_kpi(self, user):
        """Obtener u crear objetivos KPI para el usuario"""
        if user.taller:
            objetivo, created = ObjetivoKPI.objects.get_or_create(
                taller=user.taller,
                defaults={
                    'tasa_rotacion_objetivo': 1.5,
                    'dias_en_mano_objetivo': 60,
                    'dead_stock_objetivo': 10.0,
                    'dias_dead_stock': 730
                }
            )
            return objetivo

        if user.grupo:
            objetivo, created = ObjetivoKPI.objects.get_or_create(
                grupo=user.grupo,
                defaults={
                    'tasa_rotacion_objetivo': 1.5,
                    'dias_en_mano_objetivo': 60,
                    'dead_stock_objetivo': 10.0,
                    'dias_dead_stock': 730
                }
            )
            return objetivo

        return None

    def _calcular_tasa_rotacion(self, user):
        """Calcular tasa de rotación de los ÚLTIMOS 3 MESES"""
        hoy = timezone.now()
        fecha_inicio = hoy - timedelta(days=90)
        fecha_fin = hoy

        if user.taller:
            stock_filter = Q(deposito__taller=user.taller)
            movimiento_filter = Q(stock_por_deposito__deposito__taller=user.taller)
        elif user.grupo:
            from user.api.models.models import GrupoTaller
            talleres_del_grupo = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)

            stock_filter = Q(deposito__taller__in=talleres_del_grupo)
            movimiento_filter = Q(stock_por_deposito__deposito__taller__in=talleres_del_grupo)
        else:
            return None

        movimientos_egreso = Movimiento.objects.filter(
            movimiento_filter,
            tipo='EGRESO',
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('stock_por_deposito__repuesto_taller')

        ventas_totales = Decimal('0')

        for mov in movimientos_egreso:
            precio = mov.stock_por_deposito.repuesto_taller.precio
            if precio:
                ventas_totales += mov.cantidad * precio

        stocks = StockPorDeposito.objects.filter(
            stock_filter
        ).select_related('repuesto_taller')

        stock_valor = Decimal('0')

        for stock in stocks:
            precio = stock.repuesto_taller.precio
            if precio:
                stock_valor += stock.cantidad * precio

        stock_promedio = stock_valor
        tasa_rotacion = float(ventas_totales) / float(stock_promedio) if stock_promedio > 0 else 0

        return {'tasa_rotacion': round(tasa_rotacion, 2)}

    def _calcular_dias_en_mano(self, user):
        """Calcular días en mano de los ÚLTIMOS 3 MESES"""
        hoy = timezone.now()
        fecha_inicio = hoy - timedelta(days=90)
        fecha_fin = hoy
        dias_periodo = 90

        if user.taller:
            stock_filter = Q(deposito__taller=user.taller)
            movimiento_filter = Q(stock_por_deposito__deposito__taller=user.taller)
        elif user.grupo:
            from user.api.models.models import GrupoTaller
            talleres_del_grupo = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)

            stock_filter = Q(deposito__taller__in=talleres_del_grupo)
            movimiento_filter = Q(stock_por_deposito__deposito__taller__in=talleres_del_grupo)
        else:
            return None

        movimientos_egreso = Movimiento.objects.filter(
            movimiento_filter,
            tipo='EGRESO',
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('stock_por_deposito__repuesto_taller')

        ventas_totales = Decimal('0')

        for mov in movimientos_egreso:
            precio = mov.stock_por_deposito.repuesto_taller.precio
            if precio:
                ventas_totales += mov.cantidad * precio

        stocks = StockPorDeposito.objects.filter(
            stock_filter
        ).select_related('repuesto_taller')

        stock_valor = Decimal('0')

        for stock in stocks:
            precio = stock.repuesto_taller.precio
            if precio:
                stock_valor += stock.cantidad * precio

        stock_promedio = stock_valor
        ventas_diarias = float(ventas_totales) / dias_periodo if dias_periodo > 0 else 0
        dias_en_mano = float(stock_promedio) / ventas_diarias if ventas_diarias > 0 else 0

        return {'dias_en_mano': round(dias_en_mano, 1)}

    def _calcular_dead_stock(self, user, objetivo_kpi):
        """Calcular porcentaje de stock muerto"""
        fecha_limite = timezone.now() - timedelta(days=objetivo_kpi.dias_dead_stock)

        if user.taller:
            stock_filter = Q(deposito__taller=user.taller)
        elif user.grupo:
            from user.api.models.models import GrupoTaller
            talleres_del_grupo = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)

            stock_filter = Q(deposito__taller__in=talleres_del_grupo)
        else:
            return None

        total_items = StockPorDeposito.objects.filter(
            stock_filter,
            cantidad__gt=0
        ).count()

        stocks = StockPorDeposito.objects.filter(
            stock_filter,
            cantidad__gt=0
        ).select_related('repuesto_taller__repuesto')

        items_muertos = 0

        for stock in stocks:
            tiene_ventas = Movimiento.objects.filter(
                stock_por_deposito=stock,
                tipo='EGRESO'
            ).exists()

            if tiene_ventas:
                ultimo_egreso = Movimiento.objects.filter(
                    stock_por_deposito=stock,
                    tipo='EGRESO'
                ).order_by('-fecha').first()

                if ultimo_egreso and ultimo_egreso.fecha < fecha_limite:
                    items_muertos += 1

        porcentaje = round((items_muertos / total_items * 100), 1) if total_items > 0 else 0

        return porcentaje

    @action(detail=False, methods=['get'])
    def tasa_rotacion(self, request):
        """GET /api/kpis/tasa_rotacion/"""
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({"error": "Usuario sin taller ni grupo asignado"}, status=400)

        resultado = self._calcular_tasa_rotacion(user)

        if not resultado:
            return Response({"error": "No se pudieron calcular los KPIs"}, status=400)

        valor = resultado['tasa_rotacion']
        objetivo = float(objetivo_kpi.tasa_rotacion_objetivo)

        diferencia = round(valor - objetivo, 2)
        cumplimiento = round((valor / objetivo) * 100, 1) if objetivo else 0

        if cumplimiento >= 100:
            estado = "✅ Cumple"
        elif cumplimiento >= 80:
            estado = "⚡ Cerca del objetivo"
        else:
            estado = "⚠️ Por debajo del objetivo"

        return Response({
            "valor": valor,
            "objetivo": objetivo,
            "diferencia": diferencia,
            "cumplimiento_porcentaje": cumplimiento,
            "estado": estado
        })

    @action(detail=False, methods=['get'])
    def dias_en_mano(self, request):
        """GET /api/kpis/dias_en_mano/"""
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({"error": "Usuario sin taller ni grupo asignado"}, status=400)

        resultado = self._calcular_dias_en_mano(user)

        if not resultado:
            return Response({"error": "No se pudieron calcular los días en mano"}, status=400)

        valor = resultado['dias_en_mano']
        objetivo = objetivo_kpi.dias_en_mano_objetivo

        diferencia = round(valor - objetivo, 1)

        if abs(diferencia) <= 10:
            estado = "✅ Dentro del objetivo"
        elif diferencia > 10:
            estado = "⚠️ Por encima del objetivo"
        else:
            estado = "⚠️ Por debajo del objetivo"

        return Response({
            "valor": valor,
            "objetivo": objetivo,
            "diferencia": diferencia,
            "estado": estado
        })

    @action(detail=False, methods=['get'])
    def dead_stock(self, request):
        """GET /api/kpis/dead_stock/"""
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({"error": "Usuario sin taller ni grupo asignado"}, status=400)

        valor = self._calcular_dead_stock(user, objetivo_kpi)

        if valor is None:
            return Response({"error": "No se pudo calcular el dead stock"}, status=400)

        objetivo = float(objetivo_kpi.dead_stock_objetivo)

        diferencia = round(valor - objetivo, 1)

        if valor <= objetivo:
            estado = "✅ Dentro del objetivo"
        elif valor <= objetivo * 1.5:
            estado = "⚡ Ligeramente por encima"
        else:
            estado = "⚠️ Por encima del objetivo"

        return Response({
            "valor": valor,
            "objetivo": objetivo,
            "diferencia": diferencia,
            "estado": estado
        })

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """GET /api/kpis/resumen/"""
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({"error": "Usuario sin taller ni grupo asignado"}, status=400)

        tasa_rot = self._calcular_tasa_rotacion(user)
        dias_mano = self._calcular_dias_en_mano(user)
        dead_porcentaje = self._calcular_dead_stock(user, objetivo_kpi)

        if not tasa_rot or not dias_mano or dead_porcentaje is None:
            return Response({"error": "No se pudieron calcular los KPIs"}, status=400)

        return Response({
            "tasa_rotacion": {
                "valor": tasa_rot['tasa_rotacion'],
                "objetivo": float(objetivo_kpi.tasa_rotacion_objetivo)
            },
            "dias_en_mano": {
                "valor": dias_mano['dias_en_mano'],
                "objetivo": objetivo_kpi.dias_en_mano_objetivo
            },
            "dead_stock": {
                "porcentaje": dead_porcentaje,
                "objetivo": float(objetivo_kpi.dead_stock_objetivo)
            }
        })

    @action(detail=False, methods=['get', 'put'])
    def objetivos(self, request):
        """GET/PUT /api/kpis/objetivos/"""
        user = User.objects.get(id=request.session['user_id'])

        if user.grupo and user.rol_en_grupo not in ['admin']:
            if request.method == 'PUT':
                raise PermissionDenied("Solo admins del grupo pueden modificar objetivos")

        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({"error": "Usuario sin taller ni grupo asignado"}, status=400)

        if request.method == 'GET':
            serializer = ObjetivoKPISerializer(objetivo_kpi)
            return Response(serializer.data)

        elif request.method == 'PUT':
            serializer = ObjetivoKPISerializer(objetivo_kpi, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message": "Objetivos actualizados correctamente",
                    "data": serializer.data
                })

            return Response(serializer.errors, status=400)