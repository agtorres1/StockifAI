from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .serializers import MovimientosImportSerializer, StockImportSerializer, CatalogoImportSerializer, \
    DepositoSerializer
from ..models import Deposito
from ..services.import_catalogo import importar_catalogo
from ..services.import_movimientos import importar_movimientos
from django.conf import settings

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

            item = {
                "repuesto_taller": RepuestoTallerSerializer(rt).data,
                "stock_total": rt.stock_total or 0,
                "depositos": depositos_detalle,
            }
            payload.append(item)

        # Si querés validar contra RepuestoStockSerializer, se puede:
        # ser = RepuestoStockSerializer(payload, many=True)
        # return paginator.get_paginated_response(ser.data)
        return paginator.get_paginated_response(payload)