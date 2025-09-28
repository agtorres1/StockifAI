# historicos.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import warnings
from typing import Dict, List

import django
import numpy as np
import pandas as pd
import holidays
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockifai.settings')
django.setup()

from d_externo.repositories.dataexterna import obtener_todas_las_inflaciones, obtener_todos_los_patentamientos, \
    obtener_todos_los_ipsa, obtener_todas_las_prendas, obtener_todas_las_tasas_interes, obtener_todos_los_tipos_cambio

warnings.simplefilter(action="ignore", category=FutureWarning)

from inventario.repositories.movimiento_repo import MovimientoRepo
from catalogo.models import Repuesto
from inventario.repositories.repuesto_taller_repo import RepuestoTallerRepo
from user.models import Taller
from catalogo.models import RepuestoTaller

CHUNK_SIZE = 1000

def _obtener_movimientos_df(taller_id: int) -> pd.DataFrame:
    repo = MovimientoRepo()
    qs = repo.get_egresos_ultimos_5_anios(taller_id=taller_id)
    df = pd.DataFrame(list(qs))

    if df.empty:
        raise ValueError(f"No se encontraron movimientos de EGRESO para el taller_id={taller_id}.")

    df = df.rename(
        columns={
            "numero_pieza": "numero_pieza",
            "descripcion": "Descripcion",
            "fecha": "Fecha",
            "cantidad": "Cantidad",
        }
    )

    # Tipos
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.tz_localize(None)
    df = df.dropna(subset=["Fecha"])
    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0).astype(int)

    # Seguridad: nos quedamos con cantidades >= 0 para EGRESO
    df = df[df["Cantidad"] >= 0].copy()

    return df


def cargar_y_limpiar_datos_desde_repo(taller_id: int) -> pd.DataFrame:
    df = _obtener_movimientos_df(taller_id)

    # Setteo de índice temporal
    df = df.sort_values("Fecha").reset_index(drop=True)
    df["numero_pieza"] = df["numero_pieza"].astype(str)

    # Semana = lunes como inicio
    df["fecha"] = df["Fecha"].dt.to_period("W").apply(lambda r: r.start_time)
    df["fecha"] = pd.to_datetime(df["fecha"])

    # Agregación semanal por SKU
    demanda_semanal = (
        df.groupby(["numero_pieza", "fecha"], as_index=False)["Cantidad"].sum()
    )
    return demanda_semanal


def clasificar_demanda(demanda_semanal: pd.DataFrame) -> pd.DataFrame:
    """
    Genera un dataset completo (todas las semanas entre primera y última por SKU),
    """
    print("\n--- PASO 2: CLASIFICACIÓN DE DEMANDA DE SKUs ---")

    if demanda_semanal.empty:
        raise ValueError("demanda_semanal está vacío.")

    # Aseguro tipos
    demanda_semanal = demanda_semanal.copy()
    demanda_semanal["fecha"] = pd.to_datetime(demanda_semanal["fecha"])
    demanda_semanal["numero_pieza"] = demanda_semanal["numero_pieza"].astype(str)

    primeras_fechas = demanda_semanal.groupby("numero_pieza")["fecha"].min()
    fecha_final = demanda_semanal["fecha"].max()

    full_list: List[pd.DataFrame] = []
    for sku in demanda_semanal["numero_pieza"].unique():
        fechas_sku = pd.date_range(start=primeras_fechas[sku], end=fecha_final, freq="W-MON")
        df_temp = pd.DataFrame({"numero_pieza": sku, "fecha": fechas_sku})
        full_list.append(df_temp)

    df_full = pd.concat(full_list, ignore_index=True)
    df_full = df_full.merge(demanda_semanal, on=["numero_pieza", "fecha"], how="left").fillna(0)

    volumen_historico = (
        df_full.groupby("numero_pieza")
        .agg(
            fecha_inicio_registro=("fecha", "min"),
            volumen_total=("Cantidad", "sum"),
            semanas_con_venta=("Cantidad", lambda x: (x > 0).sum()),
            total_semanas_registradas=("fecha", "count"),
        )
        .reset_index()
    )
    # Obtener la fecha de la última venta (solo si Cantidad > 0)
    fecha_ultima_venta = (
        df_full[df_full["Cantidad"] > 0]
        .groupby("numero_pieza")["fecha"]
        .max()
        .rename("fecha_ultima_venta")
    )
    volumen_historico = volumen_historico.merge(
        fecha_ultima_venta, on="numero_pieza", how="left"
    )
    volumen_historico["intermitencia"] = 1 - (
            volumen_historico["semanas_con_venta"] / volumen_historico["total_semanas_registradas"]
    )

    def segmento_demanda(row):
        if row["volumen_total"] == 0:
            if row["total_semanas_registradas"] < 26:
                return "nuevo"
            return "sin_venta"
        elif row["intermitencia"] >= 0.75:  # o sea que si vendio el 25% de las semanas es frecuencia alta
            return "intermitente"
        else:
            return "frecuencia_alta"

    volumen_historico["segmento_demanda"] = volumen_historico.apply(segmento_demanda, axis=1)

    def frecuencia_rotacion(row, fecha_final):
        # Determinar la fecha de referencia para el cálculo de obsolescencia
        # Si vendió, es la última venta. Si nunca vendió, es el inicio de registro.
        if pd.isna(row["fecha_ultima_venta"]):
            fecha_referencia = row["fecha_inicio_registro"]
        else:
            fecha_referencia = row["fecha_ultima_venta"]

        dias_sin_movimiento = (fecha_final - fecha_referencia).days

        # 2. Casos de Obsolescencia y Rotación (Se aplica si registro >= 6 meses)

        # MUERTO (> 2 años sin movimiento)
        if dias_sin_movimiento > 730:
            return "MUERTO"

        # OBSOLETO (> 1 año sin movimiento)
        if dias_sin_movimiento > 365:
            return "OBSOLETO"

        # LENTO (> 6 meses y <= 1 año)
        if dias_sin_movimiento > 180:
            return "LENTO"

        # INTERMEDIO (> 2 meses y <= 6 meses)
        if dias_sin_movimiento > 60:
            return "INTERMEDIO"

        # ALTA ROTACION (<= 2 meses)
        if dias_sin_movimiento <= 60:
            return "ALTA_ROTACION"

        return "ERROR_CLASIFICACION"  # Fallback, no debería ocurrir  # Si cae fuera de las categorías explícitas

    volumen_historico["frecuencia_rotacion"] = volumen_historico.apply(
        lambda row: frecuencia_rotacion(row, fecha_final), axis=1
    )

    df_full = df_full.merge(
        volumen_historico[["numero_pieza", "segmento_demanda"]],
        on="numero_pieza",
        how="left",
    )

    print("Distribución de segmentos generada (ML):")
    print(volumen_historico["segmento_demanda"].value_counts(normalize=True))
    print("\nDistribución de 'frecuencia_rotacion' (Gestión) generada:")
    print(volumen_historico["frecuencia_rotacion"].value_counts(normalize=True))

    return df_full, volumen_historico[["numero_pieza", "frecuencia_rotacion"]]


def guardar_clasificacion_rotacion_en_db(
        taller_id: int,
        clasificacion_rotacion_df: pd.DataFrame
):
    if clasificacion_rotacion_df.empty:
        print("No hay datos de clasificación de rotación para guardar en DB.")
        return

    print(f"\n--- GUARDANDO CLASIFICACIÓN DE ROTACIÓN EN DB PARA TALLER ID: {taller_id} (USANDO BULK) ---")

    try:
        taller = Taller.objects.get(id=taller_id)
    except Taller.DoesNotExist:
        print(f"Error: Taller con ID {taller_id} no encontrado.")
        return

    repo = RepuestoTallerRepo()

    # 1. Obtener SKUs a procesar y mapeo ID -> SKU
    skus_a_procesar = clasificacion_rotacion_df["numero_pieza"].unique()

    repuestos_existentes = Repuesto.objects.filter(
        numero_pieza__in=skus_a_procesar
    ).values("id", "numero_pieza")

    sku_to_repuesto_id = {r["numero_pieza"]: r["id"] for r in repuestos_existentes}

    # Prepara el DataFrame final con IDs de Repuesto (solo los que existen)
    df_merged = clasificacion_rotacion_df.copy()
    df_merged['repuesto_id'] = df_merged['numero_pieza'].map(sku_to_repuesto_id)
    df_merged = df_merged.dropna(subset=['repuesto_id']).astype({'repuesto_id': int})

    # 2. Obtener los objetos RepuestoTaller existentes
    repuesto_ids_a_procesar = df_merged['repuesto_id'].tolist()

    rt_existentes = repo.list_by_taller_and_repuestos(taller=taller, repuesto_ids=repuesto_ids_a_procesar)
    # Mapeo: (repuesto_id -> RepuestoTaller object)
    rt_map = {rt.repuesto_id: rt for rt in rt_existentes}

    a_crear: List[RepuestoTaller] = []
    a_actualizar: List[RepuestoTaller] = []

    # 3. Preparar listas para bulk_create y bulk_update
    for _, row in df_merged.iterrows():
        repuesto_id = row['repuesto_id']
        frecuencia = row['frecuencia_rotacion']

        # Buscar el objeto RepuestoTaller existente
        rt_obj = rt_map.get(repuesto_id)

        if rt_obj:
            # Si existe, lo añadimos a la lista de actualización
            rt_obj.frecuencia = frecuencia
            a_actualizar.append(rt_obj)
        else:
            # Si NO existe, lo añadimos a la lista de creación
            # Necesitamos el objeto Repuesto para el Foreign Key
            try:
                repuesto_obj = Repuesto.objects.get(id=repuesto_id)
                a_crear.append(
                    RepuestoTaller(
                        taller=taller,
                        repuesto=repuesto_obj,
                        frecuencia=frecuencia
                    )
                )
            except Repuesto.DoesNotExist:
                warnings.warn(f"Repuesto con ID {repuesto_id} no encontrado para crear RepuestoTaller.")
                continue

    # 4. Ejecución de Bulk Operations en bloques
    with transaction.atomic():

        # 4a. Bulk Update (Actualiza existentes)
        if a_actualizar:
            print(f"-> Ejecutando bulk_update para {len(a_actualizar)} registros existentes.")
            # **IMPORTANTE:** El campo 'frecuencia' debe existir en RepuestoTaller
            RepuestoTaller.objects.bulk_update(
                a_actualizar,
                fields=['frecuencia'],
                batch_size=CHUNK_SIZE
            )

        # 4b. Bulk Create (Crea nuevos)
        if a_crear:
            print(f"-> Ejecutando bulk_create para {len(a_crear)} registros nuevos.")
            RepuestoTaller.objects.bulk_create(
                a_crear,
                batch_size=CHUNK_SIZE
            )

    total_guardados = len(a_actualizar) + len(a_crear)
    print(f"Clasificación de rotación guardada en DB (Bulk) para {total_guardados} repuestos/taller.")


def generar_caracteristicas(df_segment: pd.DataFrame) -> pd.DataFrame:
    """
    Genera variables de calendario, feriados, lags y rolling stats por segmento.
    Esta versión se enfoca en un solo segmento a la vez.
    """
    if df_segment.empty:
        raise ValueError("El DataFrame de segmento está vacío.")

    df_s = df_segment.copy()
    df_s["fecha"] = pd.to_datetime(df_s["fecha"])

    segmento = df_s["segmento_demanda"].iloc[0]
    print(f"Procesando características para segmento: '{segmento}'")

    # Fechas y feriados
    ar_holidays = holidays.AR(
        years=np.arange(df_s["fecha"].dt.year.min(), df_s["fecha"].dt.year.max() + 2)
    )
    fechas_feriados = sorted(list(ar_holidays.keys()))
    feriados_semana = {pd.Timestamp(fecha).to_period("W").start_time for fecha in fechas_feriados}

    def dias_hasta_feriado(fecha: pd.Timestamp) -> int:
        proximos_feriados = [f for f in fechas_feriados if f > fecha.date()]
        if not proximos_feriados:
            return 365
        return (proximos_feriados[0] - fecha.date()).days

    # Dummies de calendario
    df_s["mes"] = df_s["fecha"].dt.month
    df_s["semana_anio"] = df_s["fecha"].dt.isocalendar().week.astype(int)
    df_s["trimestre"] = df_s["fecha"].dt.quarter

    mes_dummies = pd.get_dummies(df_s["mes"], prefix="mes", dtype=int)
    semana_dummies = pd.get_dummies(df_s["semana_anio"], prefix="semana", dtype=int)
    trimestre_dummies = pd.get_dummies(df_s["trimestre"], prefix="trimestre", dtype=int)

    df_s = pd.concat([df_s, mes_dummies, semana_dummies, trimestre_dummies], axis=1)
    df_s = df_s.drop(columns=["mes", "semana_anio", "trimestre"])

    # Feriados y ventas
    df_s["es_semana_feriado"] = df_s["fecha"].isin(feriados_semana).astype(int)
    df_s["hubo_venta"] = (df_s["Cantidad"] > 0).astype(int)
    df_s["dias_hasta_feriado"] = df_s["fecha"].apply(dias_hasta_feriado)

    # Configuración de lags y rolling stats por segmento
    if segmento == "frecuencia_alta":
        max_lag = 52
        windows = [4, 8, 12, 26, 52]
        lags_to_generate = list(range(1, max_lag + 1))
    elif segmento == "intermitente":
        max_lag = 26
        windows = [4, 8, 12]
        lags_to_generate = list(range(1, max_lag + 1))
    else:
        windows = []
        lags_to_generate = []

    # Lags de ventas
    for lag in lags_to_generate:
        df_s[f"ventas_t_{lag}"] = df_s.groupby("numero_pieza")["Cantidad"].shift(lag)

    # Rolling stats
    for window in windows:
        rolling_series = df_s.groupby("numero_pieza")["Cantidad"].shift(1).rolling(window, min_periods=2)
        df_s[f"media_ultimas_{window}"] = rolling_series.mean()
        df_s[f"std_pasada_{window}_semanas"] = rolling_series.std()

        mean_col = f"media_ultimas_{window}"
        std_col = f"std_pasada_{window}_semanas"
        coef_var_col = f"coef_var_{window}"
        df_s[coef_var_col] = df_s[std_col] / (df_s[mean_col].replace(0, 1e-6) + 1e-6)

    return df_s


def integrar_datos_externos_base() -> pd.DataFrame:
    """
    Obtiene datos externos, calcula features y los retorna.
    Esta función NO fusiona con los datos de demanda.
    """
    print("\n--- Procesando datos externos para su futura integración ---")
    modelos_externos = [
        {"function": obtener_todas_las_inflaciones, "nombre": "inflacion", "tipo": "mensual"},
        {"function": obtener_todos_los_patentamientos, "nombre": "patentamientos", "tipo": "anual"},
        {"function": obtener_todos_los_ipsa, "nombre": "ipsa", "tipo": "mensual"},
        {"function": obtener_todas_las_prendas, "nombre": "prenda", "tipo": "mensual"},
        {"function": obtener_todas_las_tasas_interes, "nombre": "tasa_de_interes", "tipo": "mensual"},
        {"function": obtener_todos_los_tipos_cambio, "nombre": "tipo_de_cambio", "tipo": "mensual"},
    ]

    df_final = pd.DataFrame()
    for config in modelos_externos:
        helper_function = config["function"]
        new_col_name = config["nombre"]
        print(f" - Procesando: {helper_function.__name__}...")

        try:
            data_list = helper_function()
            if not data_list:
                warnings.warn(f"No se encontraron datos usando '{helper_function.__name__}'. Se omite.")
                continue

            df_ext = pd.DataFrame(data_list)

            if new_col_name == 'inflacion':
                df_ext = df_ext.rename(columns={'ipc': new_col_name})
            elif new_col_name == 'patentamientos':
                df_ext = df_ext.rename(columns={'cantidad': new_col_name})
            elif new_col_name == 'ipsa':
                df_ext = df_ext.rename(columns={'ipsa': new_col_name})
            elif new_col_name == 'tasa_de_interes':
                df_ext = df_ext.rename(columns={'tasa_interes': new_col_name})
            elif new_col_name == 'prenda':
                df_ext = df_ext.rename(columns={'prenda': new_col_name})
            elif new_col_name == 'tipo_de_cambio':
                df_ext = df_ext.rename(columns={'tipo_cambio': new_col_name})

            df_ext["fecha"] = pd.to_datetime(df_ext["fecha"])
            df_ext[new_col_name] = pd.to_numeric(df_ext[new_col_name], errors='coerce')
            df_ext = df_ext.dropna().sort_values("fecha")

            if config["tipo"] == "anual":
                lags = [12, 24, 36]
                ema_spans = [12, 24]
            else:
                lags = [1, 2, 3, 6]
                ema_spans = [3, 6, 12]

            for lag in lags:
                df_ext[f"{new_col_name}_lag_{lag}"] = df_ext[new_col_name].shift(lag)
            for span in ema_spans:
                df_ext[f"{new_col_name}_ema_{span}"] = df_ext[new_col_name].ewm(span=span, adjust=False).mean()
            df_ext[f"{new_col_name}_delta"] = df_ext[new_col_name].diff()

            df_ext = df_ext.drop(columns=[new_col_name])
            if df_final.empty:
                df_final = df_ext
            else:
                df_final = pd.merge_asof(
                    df_final.sort_values("fecha"),
                    df_ext.sort_values("fecha"),
                    on="fecha",
                    direction="backward"
                )
        except Exception as e:
            warnings.warn(f"Error procesando '{helper_function.__name__}': {e}. Se omite.")
            continue

    return df_final


def dividir_datos(
        df: pd.DataFrame, n_semanas_val: int = 4, n_semanas_test: int = 4
) -> Dict[str, pd.DataFrame]:
    """
    Divide en train/val/test por semanas, respetando el orden temporal.
    """
    print("\n--- Dividiendo datos cronológicamente en train, val y test ---")

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])

    fechas_unicas = sorted(df["fecha"].unique())

    if len(fechas_unicas) < n_semanas_val + n_semanas_test:
        raise ValueError(
            "No hay suficientes semanas para la validación y el test. "
            f"Se necesitan al menos {n_semanas_val + n_semanas_test} semanas."
        )

    split_point_test = fechas_unicas[len(fechas_unicas) - n_semanas_test]
    split_point_val = fechas_unicas[len(fechas_unicas) - n_semanas_test - n_semanas_val]

    train_df = df[df["fecha"] < split_point_val].copy()
    val_df = df[(df["fecha"] >= split_point_val) & (df["fecha"] < split_point_test)].copy()
    test_df = df[df["fecha"] >= split_point_test].copy()

    print(
        f"Conjunto de Entrenamiento: Desde {train_df['fecha'].min().date()} hasta {train_df['fecha'].max().date()}"
    )
    print(
        f"Conjunto de Validación:   Desde {val_df['fecha'].min().date()} hasta {val_df['fecha'].max().date()}"
    )
    print(
        f"Conjunto de Test:         Desde {test_df['fecha'].min().date()} hasta {test_df['fecha'].max().date()}"
    )

    return {"train": train_df, "val": val_df, "test": test_df}


def ejecutar_preproceso(
        taller_id: int,
        output_dir_base: str = "models",
) -> Dict[str, Dict[str, pd.DataFrame]]:
    print(f"\n--- INICIANDO PIPELINE DE PREPROCESAMIENTO PARA EL TALLER: (id={taller_id}) ---")

    # 1) Extraer y agregar semanal
    try:
        demanda_semanal = cargar_y_limpiar_datos_desde_repo(taller_id)
        if demanda_semanal.empty:
            raise ValueError("No hay datos de demanda semanal.")
    except ValueError as e:
        print(f"Error: {e}")
        return {}

    # 2) Clasificar
    df_full, clasificacion_rotacion_df = clasificar_demanda(demanda_semanal)
    print("Guardando clasificaciones...")
    # 3) Guardar la clasificación de rotación en la DB
    guardar_clasificacion_rotacion_en_db(taller_id, clasificacion_rotacion_df)

    # 4) Obtener y preprocesar los datos externos una sola vez
    df_externos = integrar_datos_externos_base()

    # 5) Bucle por cada segmento (ML: frecuencia_alta, intermitente)
    print("\n--- PASO 3: PROCESANDO DATOS Y GUARDANDO EN CARPETAS POR SEGMENTO ---")
    resultados: Dict[str, Dict[str, pd.DataFrame]] = {}

    for segmento, df_segmento in df_full.groupby("segmento_demanda", dropna=False):

        # Ignorar segmentos que no se usan para el entrenamiento
        if segmento in ["sin_venta", "nuevo"]:
            continue

        ruta_segmento = os.path.join(output_dir_base, str(taller_id), segmento)
        os.makedirs(ruta_segmento, exist_ok=True)

        try:
            # Integra los datos externos al segmento actual
            df_segmento = pd.merge_asof(
                df_segmento.sort_values("fecha"),
                df_externos.sort_values("fecha"),
                on="fecha",
                direction="backward"
            )

            # Genera las características específicas del segmento
            df_modelo_segmento = generar_caracteristicas(df_segmento)

            # Divide y guarda el resultado
            split_data = dividir_datos(df_modelo_segmento)
            resultados[segmento] = split_data

            for part_name, part_df in split_data.items():
                nombre_archivo = f"demanda_preprocesada_{segmento}_{part_name}.csv"
                ruta_guardado = os.path.join(ruta_segmento, nombre_archivo)
                part_df.to_csv(ruta_guardado, index=False)
                print(
                    f"Segmento '{segmento}' ({part_name}) guardado en '{ruta_guardado}' "
                    f"con {part_df.shape[0]} filas."
                )
        except ValueError as e:
            print(f"Advertencia: No se pudo procesar el segmento '{segmento}': {e}")
            continue

    print("\n--- PROCESO COMPLETADO ---")
    return resultados


if __name__ == "__main__":
    # parametros para probar
    TALLER_ID = 1
    OUTPUT_DIR = "models"  # donde se guardan los modelos

    ejecutar_preproceso(
        taller_id=TALLER_ID,
        output_dir_base=OUTPUT_DIR,
    )