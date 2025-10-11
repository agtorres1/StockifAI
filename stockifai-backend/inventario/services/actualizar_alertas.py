from collections import defaultdict
from django.db import transaction, connection
from django.db.models import F, Value, Case, When, IntegerField
from inventario.models import Alerta
from catalogo.models import RepuestoTaller
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from inventario.services._helpers import calcular_mos


def generar_alertas_inventario(
        stock_total: Decimal,
        pred_1: Decimal,
        mos_en_semanas: Optional[Decimal],
        frecuencia_rotacion: str
) -> List[Dict[str, Any]]:
    """
    Genera una lista de alertas activas basadas en las condiciones del inventario.
    """
    alertas_activas = []

    # 1. ALERTA CRÍTICA: Quiebre de Stock Inmediato
    if stock_total < pred_1:
        alertas_activas.append({
            "nivel": "CRÍTICO",
            "codigo": "ACCION_INMEDIATA",
            "mensaje": f"Quiebre Inminente. Stock ({stock_total}) no cubre la demanda de la próxima semana ({pred_1})."
        })

    # 2. ALERTA MEDIA: Bajo MOS
    # Se añade la condición de que no sea ya una alerta crítica para evitar duplicados.
    if mos_en_semanas is not None and Decimal('1') < mos_en_semanas <= Decimal('2.5') and not (stock_total < pred_1):
        alertas_activas.append({
            "nivel": "MEDIO",
            "codigo": "MOS_BAJO_REORDENAR",
            "mensaje": f"Bajo MOS. La cobertura es de {mos_en_semanas:.2f} semanas."
        })

    # 3. ALERTA INFORMATIVA: Sobre-Abastecimiento o Riesgo de Lento
    if mos_en_semanas is not None:
        es_lento_o_intermedio = frecuencia_rotacion in ["LENTO", "INTERMEDIO", "OBSOLETO", "MUERTO"]
        sobre_stock_general = mos_en_semanas >= Decimal('12')
        sobre_stock_riesgoso = mos_en_semanas >= Decimal('4') and es_lento_o_intermedio

        if sobre_stock_general or sobre_stock_riesgoso:
            alertas_activas.append({
                "nivel": "INFORMATIVO",
                "codigo": "SOBRE_STOCK_RIESGO",
                "mensaje": f"Capital Inmovilizado. Cobertura de {mos_en_semanas:.2f} semanas ({frecuencia_rotacion})."
            })

    return alertas_activas


def actualizar_alertas_para_repuestos(repuesto_taller_ids: List[int]):
    """
    Analiza y actualiza las alertas (crea, resuelve) solo para una lista específica
    de IDs de RepuestoTaller. Ideal para usar después de una importación.
    """
    if not repuesto_taller_ids:
        print("No se proporcionaron IDs de repuestos para actualizar alertas. Omitiendo.")
        return

    print(f"Iniciando actualización de alertas para {len(repuesto_taller_ids)} repuestos.")

    # 1. Obtener los datos más recientes de los repuestos afectados en una sola consulta.
    # Usamos F() para referenciar el taller del propio repuesto en el filtro.
    rt_qs = RepuestoTaller.objects.filter(pk__in=repuesto_taller_ids).annotate(
        stock_total=Sum("stocks__cantidad", filter=Q(stocks__deposito__taller=F('taller')))
    ).select_related('repuesto')

    ids_alertas_que_deben_estar_activas = set()

    # 2. Iterar sobre los repuestos y determinar qué alertas deberían estar activas.
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

        mos_en_semanas = calcular_mos(stock_total, forecast_semanas)

        # Generar la lista de alertas que este repuesto debería tener AHORA.
        alertas_potenciales = generar_alertas_inventario(
            stock_total=stock_total,
            pred_1=pred_1,
            mos_en_semanas=mos_en_semanas,
            frecuencia_rotacion=frecuencia_rotacion
        )

        # 3. Sincronizar con la base de datos (crear las que falten).
        for alerta_data in alertas_potenciales:
            snapshot = {
                "stock_total": float(stock_total),
                "mos_en_semanas": float(mos_en_semanas) if mos_en_semanas else None,
                "pred_1": float(pred_1),
                "frecuencia": frecuencia_rotacion
            }

            # get_or_create previene duplicados. Si ya existe una alerta activa, no hace nada.
            # Si no existe, la crea con los valores de 'defaults'.
            alerta_obj, created = Alerta.objects.get_or_create(
                repuesto_taller=rt,
                codigo=alerta_data['codigo'],
                estado__in=[Alerta.EstadoAlerta.NUEVA, Alerta.EstadoAlerta.VISTA],
                defaults={
                    'nivel': alerta_data['nivel'],
                    'mensaje': alerta_data['mensaje'],
                    'datos_snapshot': snapshot
                }
            )

            if created:
                print(f"  [+] Nueva alerta CREADA para {rt.repuesto.numero_pieza}: {alerta_data['codigo']}")

            # Guardamos el ID de la alerta que debe permanecer activa.
            ids_alertas_que_deben_estar_activas.add(alerta_obj.id)

    # 4. Auto-resolver alertas que ya no aplican para este subconjunto de repuestos.
    # Buscamos alertas activas de estos repuestos cuyo ID NO esté en nuestra lista de "deben estar activas".
    alertas_a_resolver = Alerta.objects.filter(
        repuesto_taller_id__in=repuesto_taller_ids,
        estado__in=[Alerta.EstadoAlerta.NUEVA, Alerta.EstadoAlerta.VISTA]
    ).exclude(id__in=ids_alertas_que_deben_estar_activas)

    # Actualizamos todas las alertas a resolver en una sola consulta.
    count = alertas_a_resolver.update(
        estado=Alerta.EstadoAlerta.RESUELTA,
        fecha_resolucion=timezone.now()
    )

    if count > 0:
        print(f"  [*] {count} alertas antiguas fueron RESUELTAS.")

    print("Actualización de alertas finalizada.")
