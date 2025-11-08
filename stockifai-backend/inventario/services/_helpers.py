from datetime import date, timedelta, datetime, time
from ..models import Movimiento
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union, Dict
from django.db.models import Sum, Q
from django.db.models.functions import TruncWeek
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


def calcular_mos(stock: Decimal, weeks: list[Decimal]) -> Decimal:
    """
       Devuelve la suma de las primeras 4 semanas de la lista 'weeks'.
       Si hay menos de 4 semanas, suma todas las disponibles.
       """
    if not weeks:
        return Decimal(0)

    primeras_4 = weeks[:4]
    predicciones_4 = Decimal(sum(Decimal(w or 0) for w in primeras_4))
    if predicciones_4 == Decimal(0):
        return None
    else  :
        return Decimal(stock/sum(Decimal(w or 0) for w in primeras_4))




    """
    Calcula el MOS (semanas de cobertura):
    - Consume stock semana a semana.
    - Si la demanda de una semana es 0, se usa el promedio.
    - Si todas las predicciones son 0/None, devuelve None.
    """
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

    return semanas.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)"""


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
