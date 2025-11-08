# inventario/api/views/kpis.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from inventario.models import Movimiento, StockPorDeposito, ObjetivoKPI
from inventario.api.serializers import ObjetivoKPISerializer
from user.api.models.models import Taller, User


class KPIsViewSet(viewsets.ViewSet):

    def _get_objetivo_kpi(self, user):
        """Obtener u crear objetivos KPI para el usuario"""
        if user.taller:
            objetivo, created = ObjetivoKPI.objects.get_or_create(
                taller=user.taller,
                defaults={
                    'tasa_rotacion_objetivo': 1.5,  # 1.5 veces en 3 meses
                    'dias_en_mano_objetivo': 60,
                    'dias_dead_stock': 730  # 2 años
                }
            )
            return objetivo

        if user.grupo:
            objetivo, created = ObjetivoKPI.objects.get_or_create(
                grupo=user.grupo,
                defaults={
                    'tasa_rotacion_objetivo': 1.5,
                    'dias_en_mano_objetivo': 60,
                    'dias_dead_stock': 730
                }
            )
            return objetivo

        return None

    def _calcular_tasa_rotacion(self, user):
        """
        Calcular tasa de rotación de los ÚLTIMOS 3 MESES
        Fórmula: Ventas (en $) / Stock Promedio (en $)
        """

        # PERÍODO FIJO: Últimos 90 días
        hoy = timezone.now()
        fecha_inicio = hoy - timedelta(days=90)
        fecha_fin = hoy

        # Filtrar por taller o grupo
        if user.taller:
            stock_filter = Q(deposito__taller=user.taller)
            movimiento_filter = Q(stock_por_deposito__deposito__taller=user.taller)
        elif user.grupo:
            from user.models import GrupoTaller
            talleres_del_grupo = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)

            stock_filter = Q(deposito__taller__in=talleres_del_grupo)
            movimiento_filter = Q(stock_por_deposito__deposito__taller__in=talleres_del_grupo)
        else:
            return None

        # 1. VENTAS de los últimos 90 días (en pesos)
        movimientos_egreso = Movimiento.objects.filter(
            movimiento_filter,
            tipo='EGRESO',
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('stock_por_deposito__repuesto_taller')

        ventas_totales = Decimal('0')
        repuestos_sin_precio = 0

        for mov in movimientos_egreso:
            precio = mov.stock_por_deposito.repuesto_taller.precio
            if precio:
                ventas_totales += mov.cantidad * precio
            else:
                repuestos_sin_precio += 1

        # 2. STOCK PROMEDIO actual (en pesos)
        stocks = StockPorDeposito.objects.filter(
            stock_filter
        ).select_related('repuesto_taller')

        stock_valor = Decimal('0')

        for stock in stocks:
            precio = stock.repuesto_taller.precio
            if precio:
                stock_valor += stock.cantidad * precio

        stock_promedio = stock_valor

        # 3. TASA DE ROTACIÓN
        tasa_rotacion = float(ventas_totales) / float(stock_promedio) if stock_promedio > 0 else 0

        return {
            'tasa_rotacion': round(tasa_rotacion, 2),
            'ventas_totales': round(float(ventas_totales), 2),
            'stock_promedio': round(float(stock_promedio), 2),
            'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
            'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
            'repuestos_sin_precio': repuestos_sin_precio
        }

    def _calcular_dias_en_mano(self, user):
        """
        Calcular días en mano de los ÚLTIMOS 3 MESES
        Fórmula: Stock Promedio / Ventas Diarias
        """

        # PERÍODO FIJO: Últimos 90 días
        hoy = timezone.now()
        fecha_inicio = hoy - timedelta(days=90)
        fecha_fin = hoy
        dias_periodo = 90

        # Filtrar por taller o grupo
        if user.taller:
            stock_filter = Q(deposito__taller=user.taller)
            movimiento_filter = Q(stock_por_deposito__deposito__taller=user.taller)
        elif user.grupo:
            from user.models import GrupoTaller
            talleres_del_grupo = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)

            stock_filter = Q(deposito__taller__in=talleres_del_grupo)
            movimiento_filter = Q(stock_por_deposito__deposito__taller__in=talleres_del_grupo)
        else:
            return None

        # 1. VENTAS de los últimos 90 días (en pesos)
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

        # 2. STOCK PROMEDIO actual (en pesos)
        stocks = StockPorDeposito.objects.filter(
            stock_filter
        ).select_related('repuesto_taller')

        stock_valor = Decimal('0')

        for stock in stocks:
            precio = stock.repuesto_taller.precio
            if precio:
                stock_valor += stock.cantidad * precio

        stock_promedio = stock_valor

        # 3. VENTAS DIARIAS
        ventas_diarias = float(ventas_totales) / dias_periodo if dias_periodo > 0 else 0

        # 4. DÍAS EN MANO
        dias_en_mano = float(stock_promedio) / ventas_diarias if ventas_diarias > 0 else 0

        return {
            'dias_en_mano': round(dias_en_mano, 1),
            'stock_promedio': round(float(stock_promedio), 2),
            'ventas_totales': round(float(ventas_totales), 2),
            'ventas_diarias': round(ventas_diarias, 2),
            'dias_periodo': dias_periodo
        }

    def _calcular_dead_stock(self, user, objetivo_kpi):
        """
        Identificar stock muerto:
        - Repuestos con ventas previas
        - Sin ventas en los últimos 2 años (730 días)
        """

        # PERÍODO: 2 años = 730 días (configurable desde objetivo_kpi)
        fecha_limite = timezone.now() - timedelta(days=objetivo_kpi.dias_dead_stock)

        # Filtrar por taller o grupo
        if user.taller:
            stock_filter = Q(deposito__taller=user.taller)
        elif user.grupo:
            from user.models import GrupoTaller
            talleres_del_grupo = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)

            stock_filter = Q(deposito__taller__in=talleres_del_grupo)
        else:
            return None

        # Obtener stocks con cantidad > 0
        stocks = StockPorDeposito.objects.filter(
            stock_filter,
            cantidad__gt=0
        ).select_related('repuesto_taller__repuesto', 'deposito')

        dead_stock_list = []
        valor_total_inmovilizado = Decimal('0')

        for stock in stocks:
            # Buscar si tiene historial de ventas
            tiene_ventas_previas = Movimiento.objects.filter(
                stock_por_deposito=stock,
                tipo='EGRESO'
            ).exists()

            # Solo considerar si YA tuvo ventas
            if tiene_ventas_previas:
                # Buscar último EGRESO
                ultimo_egreso = Movimiento.objects.filter(
                    stock_por_deposito=stock,
                    tipo='EGRESO'
                ).order_by('-fecha').first()

                # Si el último egreso fue hace más de X días → Dead Stock
                if ultimo_egreso and ultimo_egreso.fecha < fecha_limite:
                    dias_sin_venta = (timezone.now() - ultimo_egreso.fecha).days

                    # Calcular valor inmovilizado
                    precio = stock.repuesto_taller.precio if stock.repuesto_taller.precio else Decimal('0')
                    valor_inmovilizado = stock.cantidad * precio

                    dead_stock_list.append({
                        'repuesto_id': stock.repuesto_taller.repuesto.id,
                        'numero_pieza': stock.repuesto_taller.repuesto.numero_pieza,
                        'descripcion': stock.repuesto_taller.repuesto.descripcion,
                        'deposito': stock.deposito.nombre,
                        'stock_actual': stock.cantidad,
                        'dias_sin_venta': dias_sin_venta,
                        'ultimo_egreso': ultimo_egreso.fecha.strftime('%Y-%m-%d'),
                        'precio_unitario': float(precio),
                        'valor_inmovilizado': float(valor_inmovilizado)
                    })

                    valor_total_inmovilizado += valor_inmovilizado

        # Ordenar por valor inmovilizado (mayor a menor)
        dead_stock_list.sort(key=lambda x: x['valor_inmovilizado'], reverse=True)

        return {
            'total_items': len(dead_stock_list),
            'valor_total_inmovilizado': float(valor_total_inmovilizado),
            'dias_configurados': objetivo_kpi.dias_dead_stock,
            'criterio': f'Repuestos con ventas previas sin vender en {objetivo_kpi.dias_dead_stock} días',
            'items': dead_stock_list
        }

    # ===== ENDPOINTS =====

    @action(detail=False, methods=['get'])
    def tasa_rotacion(self, request):
        """
        GET /api/kpis/tasa-rotacion/

        Calcula la tasa de rotación de los últimos 3 meses
        """
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({
                "error": "Usuario sin taller ni grupo asignado"
            }, status=400)

        resultado = self._calcular_tasa_rotacion(user)

        if not resultado:
            return Response({
                "error": "No se pudieron calcular los KPIs"
            }, status=400)

        # Comparar con objetivo
        cumplimiento = round(
            (resultado['tasa_rotacion'] / float(objetivo_kpi.tasa_rotacion_objetivo)) * 100, 1
        ) if objetivo_kpi.tasa_rotacion_objetivo else 0

        response_data = {
            "tasa_rotacion": resultado['tasa_rotacion'],
            "objetivo": float(objetivo_kpi.tasa_rotacion_objetivo),
            "cumplimiento_porcentaje": cumplimiento,
            "estado": "✅ Cumple" if cumplimiento >= 100 else "⚠️ Por debajo del objetivo",
            "ventas_ultimos_3_meses": resultado['ventas_totales'],
            "stock_promedio": resultado['stock_promedio'],
            "periodo": {
                "descripcion": "Últimos 3 meses (90 días)",
                "fecha_inicio": resultado['fecha_inicio'],
                "fecha_fin": resultado['fecha_fin']
            }
        }

        if resultado['repuestos_sin_precio'] > 0:
            response_data['advertencia'] = f"⚠️ {resultado['repuestos_sin_precio']} movimientos sin precio asignado"

        return Response(response_data)

    @action(detail=False, methods=['get'])
    def dias_en_mano(self, request):
        """
        GET /api/kpis/dias-en-mano/

        Calcula los días en mano del inventario (últimos 3 meses)
        """
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({
                "error": "Usuario sin taller ni grupo asignado"
            }, status=400)

        resultado = self._calcular_dias_en_mano(user)

        if not resultado:
            return Response({
                "error": "No se pudieron calcular los días en mano"
            }, status=400)

        # Comparar con objetivo
        diferencia = resultado['dias_en_mano'] - objetivo_kpi.dias_en_mano_objetivo

        return Response({
            "dias_en_mano": resultado['dias_en_mano'],
            "objetivo": objetivo_kpi.dias_en_mano_objetivo,
            "diferencia": round(diferencia, 1),
            "estado": "✅ Dentro del objetivo" if abs(diferencia) <= 10 else "⚠️ Fuera del objetivo",
            "interpretacion": self._interpretar_dias_en_mano(resultado['dias_en_mano']),
            "stock_promedio": resultado['stock_promedio'],
            "ventas_totales": resultado['ventas_totales'],
            "ventas_diarias": resultado['ventas_diarias'],
            "periodo": {
                "descripcion": "Últimos 3 meses (90 días)",
                "dias": resultado['dias_periodo']
            }
        })

    @action(detail=False, methods=['get'])
    def dead_stock(self, request):
        """
        GET /api/kpis/dead-stock/

        Identifica repuestos con ventas previas sin vender en 2 años
        """
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({
                "error": "Usuario sin taller ni grupo asignado"
            }, status=400)

        resultado = self._calcular_dead_stock(user, objetivo_kpi)

        if not resultado:
            return Response({
                "error": "No se pudo calcular el dead stock"
            }, status=400)

        return Response({
            "total_items": resultado['total_items'],
            "valor_total_inmovilizado": resultado['valor_total_inmovilizado'],
            "dias_sin_venta_configurado": resultado['dias_configurados'],
            "criterio": resultado['criterio'],
            "items": resultado['items'],
            "recomendacion": self._recomendar_accion_dead_stock(resultado['total_items'])
        })

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """
        GET /api/kpis/resumen/

        Devuelve todos los KPIs en un solo endpoint
        """
        user = User.objects.get(id=request.session['user_id'])
        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({
                "error": "Usuario sin taller ni grupo asignado"
            }, status=400)

        # Calcular todos los KPIs
        tasa_rot = self._calcular_tasa_rotacion(user)
        dias_mano = self._calcular_dias_en_mano(user)
        dead = self._calcular_dead_stock(user, objetivo_kpi)

        if not tasa_rot or not dias_mano or not dead:
            return Response({
                "error": "No se pudieron calcular los KPIs"
            }, status=400)

        return Response({
            "tasa_rotacion": {
                "valor": tasa_rot['tasa_rotacion'],
                "objetivo": float(objetivo_kpi.tasa_rotacion_objetivo),
                "cumplimiento": round(
                    (tasa_rot['tasa_rotacion'] / float(objetivo_kpi.tasa_rotacion_objetivo)) * 100, 1
                ) if objetivo_kpi.tasa_rotacion_objetivo else 0
            },
            "dias_en_mano": {
                "valor": dias_mano['dias_en_mano'],
                "objetivo": objetivo_kpi.dias_en_mano_objetivo,
                "diferencia": round(dias_mano['dias_en_mano'] - objetivo_kpi.dias_en_mano_objetivo, 1)
            },
            "dead_stock": {
                "total_items": dead['total_items'],
                "valor_inmovilizado": dead['valor_total_inmovilizado']
            },
            "periodo": "Últimos 3 meses (90 días)"
        })

    @action(detail=False, methods=['get', 'put'])
    def objetivos(self, request):
        """
        GET /api/kpis/objetivos/ - Ver objetivo
        PUT /api/kpis/objetivos/ - Actualizar objetivo
        """
        user = User.objects.get(id=request.session['user_id'])

        if user.grupo and user.rol_en_grupo not in ['admin']:
            if request.method == 'PUT':
                raise PermissionDenied("Solo admins del grupo pueden modificar objetivos")

        objetivo_kpi = self._get_objetivo_kpi(user)

        if not objetivo_kpi:
            return Response({
                "error": "Usuario sin taller ni grupo asignado"
            }, status=400)

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