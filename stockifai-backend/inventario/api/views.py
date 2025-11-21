import logging
import math
from datetime import date, timedelta, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Set, Union
from collections import defaultdict
from user.permissions import PermissionChecker
import pandas as pd

from django.conf import settings
from django.db import transaction
from django.db.models import F, Prefetch, Q, Sum, Count, Avg
from django.db.models.expressions import Case, Value, When
from django.db.models.fields import IntegerField, DecimalField
from django.db.models.functions import TruncWeek
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from AI.services.forecast_pipeline import ejecutar_forecast_pipeline_por_taller, ejecutar_forecast_talleres
from catalogo.models import Repuesto, RepuestoTaller
from inventario.models import Deposito, Movimiento, StockPorDeposito, Alerta, ObjetivoKPI
from user.models import Grupo, GrupoTaller, Taller
from user.api.models.models import User

from ..services._helpers import (
    MESES_ABREV,
    batch_calculate_demand,
    calcular_mos,
    compute_trend_line,
    get_historical_demand,
    get_month_ranges,
)
from ..services.actualizar_alertas import actualizar_alertas_para_repuestos, generar_alertas_inventario
from ..services.import_catalogo import importar_catalogo
from ..services.import_precios import importar_precios
from ..services.import_movimientos import importar_movimientos
from ..services.import_stock import importar_stock
from .serializers import (
    AlertaSerializer,
    CatalogoImportSerializer,
    PreciosImportSerializer,
    DepositoSerializer,
    MovimientosImportSerializer,
    ObjetivoKPISerializer,
    RepuestoStockSerializer,
    RepuestoTallerSerializer,
    StockDepositoDetalleSerializer,
    StockImportSerializer,
    TallerConStockSerializer,
)

logger = logging.getLogger(__name__)


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

class ImportarPreciosView(APIView):
    def post(self, request):
        ser = PreciosImportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            res = importar_precios(
                file=ser.validated_data["file"],
                taller_id=ser.validated_data["taller_id"],
                fields_map=ser.validated_data.get("fields_map"),
            )
        except ValueError as ex:
            return Response({"error": str(ex)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(res, status=status.HTTP_200_OK)


class DepositosPorTallerView(APIView):
    def get(self, request, taller_id: int):
        qs = Deposito.objects.filter(taller_id=taller_id)
        data = DepositoSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class GrupoDetailView(APIView):
    def get(self, request, grupo_id):
        grupo = get_object_or_404(Grupo, id_grupo=grupo_id)

        # Contar talleres del grupo
        talleres_count = GrupoTaller.objects.filter(id_grupo=grupo).count()

        return Response({
            'id': grupo.id_grupo,
            'nombre': grupo.nombre,
            'descripcion': grupo.descripcion,
            'total_talleres': talleres_count,
            'stock_inicial_cargado': True  # Por ahora siempre True para grupos
        })

class DepositosPorGrupoView(APIView):
    """
    Obtiene todos los depósitos de todos los talleres que pertenecen a un grupo
    """

    def get(self, request, grupo_id):
        # Verificar que el grupo existe
        grupo = get_object_or_404(Grupo, id_grupo=grupo_id)

        # Obtener todos los talleres del grupo a través de la tabla intermedia
        talleres_ids = GrupoTaller.objects.filter(
            id_grupo=grupo
        ).values_list('id_taller', flat=True)

        # Obtener todos los depósitos de esos talleres
        depositos = Deposito.objects.filter(
            taller_id__in=talleres_ids
        ).select_related('taller')  # Optimización para traer info del taller

        # Serializar los depósitos
        serializer = DepositoSerializer(depositos, many=True)

        return Response({
            'grupo': grupo.nombre,
            'total_talleres': len(talleres_ids),
            'total_depositos': depositos.count(),
            'depositos': serializer.data
        })


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
        # ===== AGREGAR FILTRO DE PERMISOS =====
        user = PermissionChecker.get_user_from_session(request)

        # Verificar que el usuario pueda ver este taller
        try:
            from user.api.models.models import Taller
            taller = Taller.objects.get(id=taller_id)

            if not PermissionChecker.puede_ver_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para ver este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response(
                {"error": "Taller no encontrado"},
                status=404
            )
        # ===== FIN FILTRO =====

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


class LocalizarRepuestoView(APIView):
    """Localiza talleres dentro del grupo del taller solicitante con stock disponible."""

    def get(self, request, taller_id: int) -> Response:
        user = PermissionChecker.get_user_from_session(request)

        taller_origen = get_object_or_404(Taller, pk=taller_id)

        if not PermissionChecker.puede_ver_taller(user, taller_origen):
            return Response(
                {"error": "No tienes permiso para ver este taller"},
                status=403
            )

        numero_pieza = request.query_params.get("numero_pieza")
        repuesto_id = request.query_params.get("repuesto_id")

        if not numero_pieza and not repuesto_id:
            return Response(
                {"detail": "Debe indicar numero_pieza o repuesto_id como parámetro de búsqueda."},
                status=status.HTTP_400_BAD_REQUEST,
            )


        if repuesto_id:
            repuesto = get_object_or_404(Repuesto, pk=repuesto_id)
        else:
            repuesto = (
                Repuesto.objects.filter(numero_pieza__iexact=numero_pieza).first()
            )
            if not repuesto:
                return Response(
                    {"detail": "No se encontró un repuesto con ese número de pieza."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        grupos_permitidos = self._grupos_permitidos_para_taller(taller_origen)

        rt_qs = (
            RepuestoTaller.objects
            .filter(repuesto=repuesto)
            .select_related("taller")
            .prefetch_related(
                Prefetch(
                    "taller__grupotaller_set",
                    queryset=GrupoTaller.objects.select_related("id_grupo__grupo_padre"),
                    to_attr="prefetched_grupos",
                )
            )
            .annotate(
                stock_total=Sum(
                    "stocks__cantidad",
                    filter=Q(stocks__deposito__taller_id=F("taller_id"))
                )
            )
            .filter(stock_total__gt=0)
        )

        if grupos_permitidos:
            talleres_permitidos = set(
                GrupoTaller.objects.filter(id_grupo_id__in=grupos_permitidos)
                .values_list("id_taller_id", flat=True)
            )
            if talleres_permitidos:
                rt_qs = rt_qs.filter(taller_id__in=talleres_permitidos)
            else:
                rt_qs = rt_qs.none()

        resultados: List[Dict[str, Any]] = []
        total_cantidad = 0

        for rt in rt_qs:
            cantidad = int(rt.stock_total or 0)
            total_cantidad += cantidad
            taller = rt.taller

            grupos = []
            for gt in getattr(taller, "prefetched_grupos", []):
                grupo = gt.id_grupo
                grupos.append({
                    "id": grupo.id_grupo,
                    "nombre": grupo.nombre,
                    "descripcion": grupo.descripcion,
                    "grupo_padre_id": grupo.grupo_padre_id,
                    "es_subgrupo": grupo.grupo_padre_id is not None,
                })

            distancia = self._calcular_distancia_km(taller_origen, taller)

            resultados.append({
                "id": taller.id,
                "nombre": taller.nombre,
                "direccion": taller.direccion,
                "direccion_normalizada": taller.direccion_normalizada,
                "telefono": taller.telefono,
                "telefono_e164": taller.telefono_e164,
                "email": taller.email,
                "latitud": float(taller.latitud) if taller.latitud is not None else None,
                "longitud": float(taller.longitud) if taller.longitud is not None else None,
                "cantidad": cantidad,
                "distancia_km": distancia,
                "grupos": grupos,
            })

        resultados.sort(
            key=lambda item: (
                item["distancia_km"] is None,
                item["distancia_km"] or 0.0,
                -item["cantidad"],
                item["nombre"],
            )
        )

        payload = {
            "repuesto": {
                "id": repuesto.id,
                "numero_pieza": repuesto.numero_pieza,
                "descripcion": repuesto.descripcion,
            },
            "taller_origen": {
                "id": taller_origen.id,
                "nombre": taller_origen.nombre,
                "latitud": float(taller_origen.latitud) if taller_origen.latitud is not None else None,
                "longitud": float(taller_origen.longitud) if taller_origen.longitud is not None else None,
            },
            "total_cantidad": total_cantidad,
            "talleres": TallerConStockSerializer(resultados, many=True).data,
        }

        return Response(payload, status=status.HTTP_200_OK)

    @staticmethod
    def _calcular_distancia_km(origen: Taller, destino: Taller) -> Optional[float]:
        if (
            origen.latitud is None
            or origen.longitud is None
            or destino.latitud is None
            or destino.longitud is None
        ):
            return None

        lat1 = math.radians(float(origen.latitud))
        lon1 = math.radians(float(origen.longitud))
        lat2 = math.radians(float(destino.latitud))
        lon2 = math.radians(float(destino.longitud))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        radio_tierra_km = 6371.0
        return round(radio_tierra_km * c, 2)

    def _grupos_permitidos_para_taller(self, taller: Taller) -> Set[int]:
        grupos_asignados = list(
            GrupoTaller.objects.filter(id_taller=taller).values_list("id_grupo_id", flat=True)
        )
        if not grupos_asignados:
            return set()

        grupos = list(
            Grupo.objects.all().values("id_grupo", "grupo_padre_id")
        )

        parent_map = {g["id_grupo"]: g["grupo_padre_id"] for g in grupos}
        children_map: Dict[Optional[int], List[int]] = {}
        for g in grupos:
            parent = g["grupo_padre_id"]
            children_map.setdefault(parent, []).append(g["id_grupo"])

        roots: Set[int] = set()
        for gid in grupos_asignados:
            current = gid
            while current is not None:
                parent = parent_map.get(current)
                if parent is None:
                    roots.add(current)
                    break
                current = parent

        permitidos: Set[int] = set()
        stack = list(roots)
        while stack:
            gid = stack.pop()
            if gid in permitidos:
                continue
            permitidos.add(gid)
            stack.extend(children_map.get(gid, []))

        return permitidos

class EjecutarForecastPorTallerView(APIView):
    def post(self, request, taller_id: int):
        user = PermissionChecker.get_user_from_session(request)

        try:
            taller = Taller.objects.get(id=taller_id)
            if not PermissionChecker.puede_editar_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para ejecutar forecast en este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)


        fecha_lunes = request.data.get("fecha_lunes")  # "YYYY-MM-DD" (lunes)

        out = ejecutar_forecast_pipeline_por_taller(taller_id, fecha_lunes)
        return Response({"status": "ok", "details": out}, status=status.HTTP_200_OK)

class EjecutarForecastView(APIView):
    def post(self, request):
        fecha_lunes = request.data.get("fecha_lunes")  # "YYYY-MM-DD" (lunes)

        out = ejecutar_forecast_talleres(fecha_lunes)
        return Response({"status": "ok", "details": out}, status=status.HTTP_200_OK)



class KPIsViewSet(viewsets.ViewSet):

    def _get_objetivo_kpi(self, taller_id):
        """Obtener u crear objetivos KPI para un taller específico"""
        if not taller_id:
            return None

        objetivo, created = ObjetivoKPI.objects.get_or_create(
            taller_id=taller_id,
            defaults={
                'tasa_rotacion_objetivo': 1.5,
                'dias_en_mano_objetivo': 30,
                'dead_stock_objetivo': 10.0,
                'dias_dead_stock': 730
            }
        )
        return objetivo

    def _calcular_dead_stock_desde_salud(self, request, taller_id):
        """Calcula dead stock usando SaludInventarioPorCategoriaView - POR VALOR"""
        from inventario.api.views import SaludInventarioPorCategoriaView

        salud_view = SaludInventarioPorCategoriaView()
        salud_response = salud_view.get(request, taller_id=int(taller_id))
        salud_data = salud_response.data

        total_valor = 0
        valor_sobrestock = 0

        for categoria in salud_data:
            for freq_key, freq_data in categoria.get("frecuencias", {}).items():
                valor_freq = freq_data.get("total_valor_frecuencia", 0)
                total_valor += valor_freq

                # Si la frecuencia es MUERTO, todo su valor es dead stock
                if freq_key == "MUERTO":
                    valor_sobrestock += valor_freq

        resultado = round((valor_sobrestock / total_valor * 100), 1) if total_valor > 0 else 0

        print(f"🔍 DEAD STOCK POR VALOR: ${valor_sobrestock:.2f}/${total_valor:.2f} = {resultado}%")

        return resultado

    def _calcular_tasa_rotacion(self, taller_id):
        """Calcular tasa de rotación de los ÚLTIMOS 3 MESES para un taller específico - OPTIMIZADO"""
        if not taller_id:
            return None

        hoy = timezone.now()
        fecha_inicio = hoy - timedelta(days=90)
        fecha_fin = hoy

        # Filtros simples por taller_id
        stock_filter = Q(deposito__taller_id=taller_id)
        movimiento_filter = Q(stock_por_deposito__deposito__taller_id=taller_id)

        # ✅ OPTIMIZACIÓN: select_related para evitar queries adicionales
        movimientos_egreso = Movimiento.objects.filter(
            movimiento_filter,
            tipo='EGRESO',
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('stock_por_deposito__repuesto_taller')

        # ✅ OPTIMIZACIÓN: Calcular en la base de datos con annotate
        ventas_totales = movimientos_egreso.aggregate(
            total=Sum(
                F('cantidad') * F('stock_por_deposito__repuesto_taller__precio'),
                output_field=DecimalField()
            )
        )['total'] or Decimal('0')

        # ✅ OPTIMIZACIÓN: select_related y calcular en la BD
        stocks = StockPorDeposito.objects.filter(
            stock_filter
        ).select_related('repuesto_taller')

        stock_valor = stocks.aggregate(
            total=Sum(
                F('cantidad') * F('repuesto_taller__precio'),
                output_field=DecimalField()
            )
        )['total'] or Decimal('0')

        stock_promedio = stock_valor
        tasa_rotacion = float(ventas_totales) / float(stock_promedio) if stock_promedio > 0 else 0

        return {'tasa_rotacion': round(tasa_rotacion, 2)}

    def _calcular_dias_en_mano(self, taller_id):
        """Calcular días en mano de los ÚLTIMOS 3 MESES para un taller específico - OPTIMIZADO"""
        if not taller_id:
            return None

        hoy = timezone.now()
        fecha_inicio = hoy - timedelta(days=90)
        fecha_fin = hoy
        dias_periodo = 90

        # Filtros simples por taller_id
        stock_filter = Q(deposito__taller_id=taller_id)
        movimiento_filter = Q(stock_por_deposito__deposito__taller_id=taller_id)

        # ✅ OPTIMIZACIÓN: Calcular ventas_totales en una sola query
        movimientos_egreso = Movimiento.objects.filter(
            movimiento_filter,
            tipo='EGRESO',
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        )

        ventas_totales = movimientos_egreso.aggregate(
            total=Sum(
                F('cantidad') * F('stock_por_deposito__repuesto_taller__precio'),
                output_field=DecimalField()
            )
        )['total'] or Decimal('0')

        # ✅ OPTIMIZACIÓN: Calcular stock_valor en una sola query
        stock_valor = StockPorDeposito.objects.filter(
            stock_filter
        ).aggregate(
            total=Sum(
                F('cantidad') * F('repuesto_taller__precio'),
                output_field=DecimalField()
            )
        )['total'] or Decimal('0')

        stock_promedio = stock_valor
        ventas_diarias = float(ventas_totales) / dias_periodo if dias_periodo > 0 else 0
        dias_en_mano = float(stock_promedio) / ventas_diarias if ventas_diarias > 0 else 0

        return {'dias_en_mano': round(dias_en_mano, 1)}


    @action(detail=False, methods=['get'])
    def tasa_rotacion(self, request):
        """GET /api/kpis/tasa_rotacion/?taller_id=123"""

        # Obtener taller_id del query param
        taller_id = request.GET.get('taller_id')

        if not taller_id:
            return Response({"error": "taller_id es requerido"}, status=400)

        # Obtener objetivo KPI para ese taller
        objetivo_kpi = self._get_objetivo_kpi(taller_id)

        if not objetivo_kpi:
            return Response({"error": "No se encontró configuración de objetivos para este taller"}, status=400)

        # Calcular tasa de rotación para ese taller
        resultado = self._calcular_tasa_rotacion(taller_id)

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
        """GET /api/kpis/dias_en_mano/?taller_id=123"""

        # Obtener taller_id del query param
        taller_id = request.GET.get('taller_id')

        if not taller_id:
            return Response({"error": "taller_id es requerido"}, status=400)

        # Obtener objetivo KPI para ese taller
        objetivo_kpi = self._get_objetivo_kpi(taller_id)

        if not objetivo_kpi:
            return Response({"error": "No se encontró configuración de objetivos para este taller"}, status=400)

        # Calcular días en mano para ese taller
        resultado = self._calcular_dias_en_mano(taller_id)

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
        """GET /api/kpis/dead_stock/?taller_id=123"""

        taller_id = request.GET.get('taller_id')

        if not taller_id:
            return Response({"error": "taller_id es requerido"}, status=400)

        # ✅ Usar el método helper
        valor = self._calcular_dead_stock_desde_salud(request, taller_id)

        # Obtener objetivo
        objetivo_kpi = self._get_objetivo_kpi(taller_id)
        objetivo = float(objetivo_kpi.dead_stock_objetivo) if objetivo_kpi else 10.0

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
        """GET /api/kpis/resumen/?taller_id=123"""

        # Obtener taller_id del query param
        taller_id = request.GET.get('taller_id')

        if not taller_id:
            return Response({"error": "taller_id es requerido"}, status=400)

        # Obtener objetivo KPI para ese taller
        objetivo_kpi = self._get_objetivo_kpi(taller_id)

        if not objetivo_kpi:
            return Response({"error": "No se encontró configuración de objetivos para este taller"}, status=400)

        # Calcular todos los KPIs para ese taller
        tasa_rot = self._calcular_tasa_rotacion(taller_id)
        dias_mano = self._calcular_dias_en_mano(taller_id)
        dead_porcentaje = self._calcular_dead_stock_desde_salud(request, taller_id)  # ← CAMBIAR AQUÍ

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

class DetalleForecastingView(APIView):
    """
    GET /talleres/<taller_id>/repuestos/<repuesto_taller_id>/forecasting
    """

    NUM_HISTORICO = 16
    NUM_FORECAST_GRAFICO = 6
    CONFIDENCE_PCT = 0.04

    def get(self, request, taller_id: int, repuesto_taller_id: int):
        # 1. Recuperar el RepuestoTaller y anotar el stock total
        user = PermissionChecker.get_user_from_session(request)

        try:
            taller = Taller.objects.get(id=taller_id)
            if not PermissionChecker.puede_ver_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para ver este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)

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
        forecast_base_data = predicciones_db

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
        user = PermissionChecker.get_user_from_session(request)

        try:
            taller = Taller.objects.get(id=taller_id)
            if not PermissionChecker.puede_ver_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para ver forecasting de este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)


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

        user = PermissionChecker.get_user_from_session(request)
        
        try:
            from user.api.models.models import Taller
            taller = Taller.objects.get(id=taller_id)

            if not PermissionChecker.puede_ver_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para ver alertas de este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)

        summary_mode = request.query_params.get("summary") == "1"

        if summary_mode:
            alertas_filtradas_qs = Alerta.objects.filter(
                repuesto_taller__taller_id=taller_id,
                estado__in=[Alerta.EstadoAlerta.NUEVA]
            )
            lista_de_niveles = list(alertas_filtradas_qs.values_list('nivel', flat=True))
            alert_counts = {
                Alerta.NivelAlerta.CRITICO: 0,
                Alerta.NivelAlerta.ADVERTENCIA: 0,
                Alerta.NivelAlerta.INFORMATIVO: 0
            }
            counts_en_python = defaultdict(int)
            for nivel in lista_de_niveles:
                counts_en_python[nivel] += 1
            for nivel, total in counts_en_python.items():
                if nivel in alert_counts:
                    alert_counts[nivel] = total

            total_urgente = alert_counts[Alerta.NivelAlerta.CRITICO]
            alert_counts["TOTAL_URGENTE"] = total_urgente
            return Response(alert_counts)
        else:
            active_alerts_qs = Alerta.objects.filter(
                repuesto_taller__taller_id=taller_id,
                estado__in=[Alerta.EstadoAlerta.NUEVA, Alerta.EstadoAlerta.VISTA]
            )
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
        # ===== AGREGAR FILTRO =====
        user = PermissionChecker.get_user_from_session(request)

        alerta = get_object_or_404(Alerta, id=alerta_id)
        taller = alerta.repuesto_taller.taller

        if not PermissionChecker.puede_ver_taller(user, taller):
            return Response(
                {"error": "No tienes permiso para descartar esta alerta"},
                status=403
            )
        # ===== FIN FILTRO =====

        alerta.estado = Alerta.EstadoAlerta.DESCARTADA
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
        # ===== AGREGAR FILTRO =====
        user = PermissionChecker.get_user_from_session(request)

        alerta = get_object_or_404(Alerta, pk=alerta_id)
        taller = alerta.repuesto_taller.taller

        if not PermissionChecker.puede_ver_taller(user, taller):
            return Response(
                {"error": "No tienes permiso para marcar esta alerta"},
                status=403
            )
        # ===== FIN FILTRO =====

        if alerta.estado == Alerta.EstadoAlerta.NUEVA:
            alerta.estado = Alerta.EstadoAlerta.VISTA
            alerta.save(update_fields=['estado'])

        return Response(
            {"status": "Alerta marcada como vista"},
            status=status.HTTP_200_OK
        )


class MarkAllAsSeenView(APIView):
    """
        POST /talleres/<taller_id>/alertas/mark-all-as-seen/

        Cambia el estado de una lista específica de alertas 'NUEVA' a 'VISTA'.
        Recibe un array de IDs en el cuerpo de la petición.
        """

    def post(self, request, taller_id: int):
        # ===== AGREGAR FILTRO =====
        user = PermissionChecker.get_user_from_session(request)

        try:
            taller = Taller.objects.get(id=taller_id)
            if not PermissionChecker.puede_ver_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para marcar alertas de este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)
        # ===== FIN FILTRO =====

        alerta_ids = request.data.get('alerta_ids')

        if not isinstance(alerta_ids, list):
            return Response(
                {"error": "Se esperaba una lista de IDs en 'alerta_ids'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not alerta_ids:
            return Response(
                {"status": "No se proporcionaron IDs para marcar."},
                status=status.HTTP_200_OK
            )

        alertas_a_marcar = Alerta.objects.filter(
            pk__in=alerta_ids,
            repuesto_taller__taller_id=taller_id,
            estado=Alerta.EstadoAlerta.NUEVA
        )
        count = alertas_a_marcar.update(estado=Alerta.EstadoAlerta.VISTA)
        return Response(
            {"status": f"{count} alertas marcadas como vistas"},
            status=status.HTTP_200_OK
        )

class AlertsForRepuestoView(APIView):
    """
    GET /talleres/<taller_id>/repuestos/<repuesto_taller_id>/alertas/

    Devuelve el historial paginado y filtrable de TODAS las alertas
    para un repuesto específico, ordenado por prioridad de estado.
    """
    pagination_class = _StockPagination

    def get(self, request, taller_id: int, repuesto_taller_id: int):
        user = PermissionChecker.get_user_from_session(request)

        try:
            taller = Taller.objects.get(id=taller_id)
            if not PermissionChecker.puede_ver_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para ver alertas de este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)

        historial_alertas = Alerta.objects.filter(
            repuesto_taller__taller_id=taller_id,
            repuesto_taller_id=repuesto_taller_id
        )
        niveles_raw = request.query_params.get('niveles')

        if niveles_raw:
            lista_de_niveles = [nivel.strip().upper() for nivel in niveles_raw.split(',')]
            historial_alertas = historial_alertas.filter(nivel__in=lista_de_niveles)

        ordered_alertas = (
            historial_alertas
            .annotate(
                estado_prio=Case(
                    When(estado=Alerta.EstadoAlerta.NUEVA, then=Value(0)),
                    When(estado=Alerta.EstadoAlerta.VISTA, then=Value(1)),
                    When(estado=Alerta.EstadoAlerta.DESCARTADA, then=Value(3)),
                    When(estado=Alerta.EstadoAlerta.RESUELTA, then=Value(2)),
                    default=Value(9),
                    output_field=IntegerField(),
                )
            )
            .select_related('repuesto_taller__repuesto')
            .order_by('estado_prio', '-fecha_creacion', '-id')
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(ordered_alertas, request, view=self)
        if page is not None:
            serializer = AlertaSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AlertaSerializer(ordered_alertas, many=True)
        return Response(serializer.data)

class ExportarUrgentesView(APIView):
    """
    GET /talleres/<taller_id>/alertas/exportar-urgentes/

    Genera un archivo Excel con los repuestos en estado CRÍTICO (quiebre inminente)
    y la cantidad sugerida a comprar para cubrir la demanda de la próxima semana.
    """
    def get(self, request, taller_id: int):

        user = PermissionChecker.get_user_from_session(request)

        try:
            taller = Taller.objects.get(id=taller_id)
            if not PermissionChecker.puede_ver_taller(user, taller):
                return Response(
                    {"error": "No tienes permiso para exportar alertas de este taller"},
                    status=403
                )
        except Taller.DoesNotExist:
            return Response({"error": "Taller no encontrado"}, status=404)

        # Alertas CRÍTICAS activas
        alertas_criticas_qs = Alerta.objects.filter(
            repuesto_taller__taller_id=taller_id,
            nivel=Alerta.NivelAlerta.CRITICO,
            estado__in=[Alerta.EstadoAlerta.NUEVA, Alerta.EstadoAlerta.VISTA]
        ).select_related(
            'repuesto_taller__repuesto'
        ).annotate(
            stock_actual=Sum("repuesto_taller__stocks__cantidad",
                             filter=Q(repuesto_taller__stocks__deposito__taller_id=taller_id),
                             output_field=DecimalField())
        )
        data_para_excel = []
        for alerta in alertas_criticas_qs:
            rt = alerta.repuesto_taller
            repuesto = rt.repuesto
            stock_total = Decimal(alerta.stock_actual or 0)
            pred_1 = Decimal(getattr(rt, 'pred_1', 0) or 0)

            # --- Cálculo de la Cantidad a Comprar ---
            cantidad_a_comprar = max(Decimal(0), pred_1 - stock_total)
            if cantidad_a_comprar > 0:
                cantidad_a_comprar = cantidad_a_comprar.to_integral_value(rounding='ROUND_CEILING')

            if cantidad_a_comprar > 0:
                data_para_excel.append({
                    "Numero Pieza": repuesto.numero_pieza,
                    "Descripcion": repuesto.descripcion,
                    "Stock Actual": stock_total,
                    "Demanda Prox. Semana": pred_1,
                    "Cantidad a Comprar": cantidad_a_comprar,
                })

        if not data_para_excel:
            return Response({"detail": "No hay repuestos con alerta crítica que requieran compra urgente."},
                            status=status.HTTP_404_NOT_FOUND)

        df = pd.DataFrame(data_para_excel)
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_archivo = f"reporte_urge_comprar_{fecha_actual}.xlsx"

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            sheet_name = 'Repuestos_Urgentes'
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_length = 0
                column_letter = col[0].column_letter
                # Calcular el ancho máximo del contenido
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                worksheet.column_dimensions[column_letter].width = max_length + 4

        return response


class SaludInventarioPorCategoriaView(APIView):
    """
    GET /api/talleres/<taller_id>/salud-por-categoria/
    Devuelve un resumen de salud (conteo por estado) y valor total,
    agrupado por categoría y frecuencia.
    """

    def get(self, request, taller_id: int):

        rt_qs = RepuestoTaller.objects.filter(
            taller_id=taller_id
        ).annotate(
            stock_total=Sum(
                "stocks__cantidad",
                filter=Q(stocks__deposito__taller_id=taller_id),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).select_related('repuesto__categoria')

        health_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        health_values = defaultdict(lambda: defaultdict(Decimal))

        NIVEL_TO_SALUD = {
            "CRÍTICO": "critico",
            "ADVERTENCIA": "advertencia",
            "INFORMATIVO": "sobrestock",
        }
        SALUD_KEYS = ["critico", "advertencia", "saludable", "sobrestock"]

        # Iterar y Clasificar cada RepuestoTaller
        for rt in rt_qs:
            stock = Decimal(rt.stock_total or 0)
            costo = Decimal(getattr(rt, 'costo', 0) or 0)
            valor_stock = stock * costo  # Valor total del stock de este repuesto

            pred_1 = Decimal(getattr(rt, 'pred_1', 0) or 0)
            frecuencia_str = getattr(rt, 'frecuencia', None) or "DESCONOCIDA"

            categoria_nombre = "Sin Categoría"
            if rt.repuesto and rt.repuesto.categoria:
                categoria_nombre = rt.repuesto.categoria.nombre

            forecast_semanas = [
                pred_1,
                Decimal(getattr(rt, 'pred_2', 0) or 0),
                Decimal(getattr(rt, 'pred_3', 0) or 0),
                Decimal(getattr(rt, 'pred_4', 0) or 0),
            ]
            mos = calcular_mos(stock, forecast_semanas)
            alertas_potenciales = generar_alertas_inventario(
                stock_total=stock, pred_1=pred_1, mos_en_semanas=mos,
                frecuencia_rotacion=frecuencia_str
            )
            if not alertas_potenciales:
                status = "saludable"
            else:
                primer_nivel_alerta = alertas_potenciales[0]['nivel']
                status = NIVEL_TO_SALUD.get(primer_nivel_alerta, "saludable")

            health_counts[categoria_nombre][frecuencia_str][status] += 1
            health_values[categoria_nombre][frecuencia_str] += valor_stock

        response_data = []
        for categoria, frecuencias_data in health_counts.items():
            categoria_obj = {
                "categoria": categoria,
                "frecuencias": {},
                "total_items_categoria": 0,
                "total_valor_categoria": Decimal(0)
            }
            total_items_categoria = 0
            total_valor_categoria = Decimal(0)

            for freq_key, counts in frecuencias_data.items():
                frecuencia_obj = {}
                total_items_frecuencia = 0

                # Obtener el valor total para esta frecuencia/categoría
                total_valor_frecuencia = health_values[categoria].get(freq_key, Decimal(0))

                # Obtener los conteos de salud
                for salud_key in SALUD_KEYS:
                    count_value = counts.get(salud_key, 0)
                    frecuencia_obj[salud_key] = count_value  # Solo el conteo
                    total_items_frecuencia += count_value

                if total_items_frecuencia > 0:
                    frecuencia_obj["total_items_frecuencia"] = total_items_frecuencia
                    frecuencia_obj["total_valor_frecuencia"] = float(total_valor_frecuencia)
                    categoria_obj["frecuencias"][freq_key] = frecuencia_obj

                    total_items_categoria += total_items_frecuencia
                    total_valor_categoria += total_valor_frecuencia

            if total_items_categoria > 0:
                categoria_obj["total_items_categoria"] = total_items_categoria
                categoria_obj["total_valor_categoria"] = float(total_valor_categoria)
                response_data.append(categoria_obj)

        response_data.sort(key=lambda x: x['categoria'])

        total_items_global = 0
        total_sobrestock_global = 0

        for categoria_data in response_data:
            for freq_key, freq_data in categoria_data.get("frecuencias", {}).items():
                total_items_global += freq_data.get("total_items_frecuencia", 0)
                total_sobrestock_global += freq_data.get("sobrestock", 0)

        porcentaje_global = round((total_sobrestock_global / total_items_global * 100),
                                  1) if total_items_global > 0 else 0

        print(f"🔍 SALUD INVENTARIO - Total items: {total_items_global}")
        print(f"🔍 SALUD INVENTARIO - Total sobrestock: {total_sobrestock_global}")
        print(f"🔍 SALUD INVENTARIO - Porcentaje: {porcentaje_global}%")

        return Response(response_data)

        return Response(response_data)

class ExportarSaludInventarioView(APIView):
    """
    GET /talleres/<taller_id>/salud-inventario/exportar/

    Genera un archivo Excel con el resumen de la salud del inventario.
    La hoja de detalle está ordenada por Frecuencia y luego por Ponderación.
    """

    def get(self, request, taller_id: int):

        rt_qs = RepuestoTaller.objects.filter(
            taller_id=taller_id
        ).annotate(
            stock_total=Sum(
                "stocks__cantidad",
                filter=Q(stocks__deposito__taller_id=taller_id),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).select_related('repuesto__categoria')

        valor_por_frecuencia = defaultdict(Decimal)
        datos_crudos_excel = []

        NIVEL_TO_SALUD = {
            "CRÍTICO": "critico",
            "ADVERTENCIA": "advertencia",
            "INFORMATIVO": "sobrestock",
        }

        for rt in rt_qs:
            stock = Decimal(rt.stock_total or 0)
            costo = Decimal(getattr(rt, 'costo', 0) or 0)
            valor_stock = stock * costo
            pred_1 = Decimal(getattr(rt, 'pred_1', 0) or 0)
            frecuencia_str = getattr(rt, 'frecuencia', None) or "DESCONOCIDA"
            categoria_nombre = "Sin Categoría"
            if rt.repuesto and rt.repuesto.categoria:
                categoria_nombre = rt.repuesto.categoria.nombre

            forecast_semanas = [
                pred_1,
                Decimal(getattr(rt, 'pred_2', 0) or 0),
                Decimal(getattr(rt, 'pred_3', 0) or 0),
                Decimal(getattr(rt, 'pred_4', 0) or 0),
            ]
            mos = calcular_mos(stock, forecast_semanas)
            alertas_potenciales = generar_alertas_inventario(
                stock_total=stock, pred_1=pred_1, mos_en_semanas=mos,
                frecuencia_rotacion=frecuencia_str
            )
            if not alertas_potenciales:
                status = "saludable"
            else:
                primer_nivel_alerta = alertas_potenciales[0]['nivel']
                status = NIVEL_TO_SALUD.get(primer_nivel_alerta, "saludable")

            valor_por_frecuencia[frecuencia_str] += valor_stock

            datos_crudos_excel.append({
                "Numero Pieza": rt.repuesto.numero_pieza,
                "Descripcion": rt.repuesto.descripcion,
                "Categoria": categoria_nombre,
                "Frecuencia": frecuencia_str,
                "Estado de Salud": status.upper(),
                "Stock Actual (U)": float(stock),
                "Costo Unitario ($)": float(costo),
                "Valor Stock ($)": float(valor_stock),
            })

        total_valor_inventario = sum(valor_por_frecuencia.values())

        for row in datos_crudos_excel:
            frecuencia_sku = row['Frecuencia']
            valor_sku = row['Valor Stock ($)']
            total_valor_grupo = valor_por_frecuencia.get(frecuencia_sku, Decimal(0))

            if total_valor_grupo > 0:
                ponderacion = (Decimal(valor_sku) / total_valor_grupo)
            else:
                ponderacion = Decimal(0)

            row['Ponderacion Frecuencia (%)'] = float(ponderacion)

        frecuencia_order = {
            "MUERTO": 0,
            "OBSOLETO": 1,
            "LENTO": 2,
            "INTERMEDIO": 3,
            "ALTA_ROTACION": 4,
            "DESCONOCIDA": 5
        }

        datos_crudos_excel.sort(key=lambda row: (
            frecuencia_order.get(row['Frecuencia'], 99),  # Clave 1: Prioridad de Frecuencia (asc)
            -row['Ponderacion Frecuencia (%)']  # Clave 2: Ponderación (desc)
        ))

        # Hoja 1: Resumen por Frecuencia
        data_resumen_frecuencia = []
        for freq, valor in valor_por_frecuencia.items():
            porcentaje_decimal = (valor / total_valor_inventario) if total_valor_inventario > 0 else 0
            data_resumen_frecuencia.append({
                "Frecuencia": freq,
                "Valor Total ($)": float(valor),
                "Porcentaje (%)": float(porcentaje_decimal)
            })
        df_resumen_frecuencia = pd.DataFrame(data_resumen_frecuencia)
        df_resumen_frecuencia['sort_key'] = df_resumen_frecuencia['Frecuencia'].map(frecuencia_order)
        df_resumen_frecuencia = df_resumen_frecuencia.sort_values(by='sort_key').drop(columns='sort_key')

        # Hoja 2: Detalle
        df_detalle = pd.DataFrame(datos_crudos_excel)

        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_archivo = f"reporte_salud_inventario_{taller_id}_{fecha_actual}.xlsx"

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df_resumen_frecuencia.to_excel(writer, sheet_name='Resumen_por_Frecuencia', index=False)
            df_detalle.to_excel(writer, sheet_name='Detalle_Inventario', index=False)

            workbook = writer.book
            ws_resumen = workbook['Resumen_por_Frecuencia']
            for cell in ws_resumen['B'][1:]:  # Columna "Valor Total ($)"
                cell.number_format = '$ #,##0.00'
            for cell in ws_resumen['C'][1:]:  # Columna "Porcentaje (%)"
                cell.number_format = '0.00%'

            ws_detalle = workbook['Detalle_Inventario']
            for cell in ws_detalle['F'][1:]:  # Columna "Stock Actual (U)"
                cell.number_format = '#,##0'
            for cell in ws_detalle['G'][1:]:  # Columna "Costo Unitario ($)"
                cell.number_format = '$ #,##0.00'
            for cell in ws_detalle['H'][1:]:  # Columna "Valor Stock ($)"
                cell.number_format = '$ #,##0.00'
            for cell in ws_detalle['I'][1:]:  # Columna "Ponderacion Frecuencia (%)"
                cell.number_format = '0.00%'

            for sheet_name in workbook.sheetnames:
                worksheet = workbook[sheet_name]
                for col in worksheet.columns:
                    max_length = 0
                    column_letter = col[0].column_letter
                    for cell in col:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    worksheet.column_dimensions[column_letter].width = max_length + 4

        return response