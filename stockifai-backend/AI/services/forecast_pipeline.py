from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List

from AI.historicos import ejecutar_preproceso
from AI.model_training import ejecutar_pipeline_entrenamiento
from AI.inferencia import ejecutar_inferencia
from user.api.models.models import Taller


def ejecutar_forecast_pipeline_por_taller(taller_id: int, fecha_lunes: datetime) -> Dict[str, Any]:
    fecha_lunes = _normalize_fecha_lunes(fecha_lunes)

    result: Dict[str, Any] = {"taller_id": taller_id, "fecha_lunes": fecha_lunes}

    print(f"\n--- PASO 1: Preproceso - Taller: {taller_id} ---")
    pp = ejecutar_preproceso(taller_id=taller_id, output_dir_base="models")
    result["preprocess"] = {"segmentos": list(pp.keys()) if pp else []}

    print("\n--- PASO 2: Entrenando modelos ---")
    ejecutar_pipeline_entrenamiento(taller_id)

    print("\n--- PASO 3: Realizando inferencias ---")
    ejecutar_inferencia(taller_id=taller_id, fecha_prediccion_str=fecha_lunes)

    print(f"\n--- Fin del forecasting - Taller: {taller_id} ---")
    return result


def ejecutar_forecast_talleres(fecha_lunes: datetime) -> Dict[str, Any]:
    ids: list[int] = list(Taller.objects.values_list("id", flat=True))
    outputs: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []

    for taller_id in ids:
        try:
            out = ejecutar_forecast_pipeline_por_taller(taller_id, fecha_lunes)
            outputs.append({"taller_id": taller_id})
        except Exception as e:
            # no frenamos toda la corrida por un taller
            errores.append({"taller_id": taller_id, "error": str(e)})

    return {"fecha_lunes": fecha_lunes, "talleres": ids, "ok": outputs, "errores": errores}


def _normalize_fecha_lunes(fecha_lunes: [datetime, str]) -> str:
    # 1. Asegurar que la entrada sea un objeto datetime (o date)
    if isinstance(fecha_lunes, str):
        # Asume el formato "YYYY-MM-DD" del request POST
        fecha_lunes = datetime.strptime(fecha_lunes, "%Y-%m-%d").date()

    # Mover al lunes anterior si no es lunes
    # weekday() devuelve 0 para lunes, 1 para martes, ..., 6 para domingo.
    if fecha_lunes.weekday() != 0:
        # Resta el número de días transcurridos desde el lunes.
        fecha_lunes -= timedelta(days=fecha_lunes.weekday())

    # Devuelve la fecha normalizada como string
    return fecha_lunes.strftime("%Y-%m-%d")
