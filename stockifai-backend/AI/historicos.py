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

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockifai.settings')
django.setup()

from d_externo.repositories.dataexterna import obtener_todas_las_inflaciones, obtener_todos_los_patentamientos, \
    obtener_todos_los_ipsa, obtener_todas_las_prendas, obtener_todas_las_tasas_interes, obtener_todos_los_tipos_cambio

warnings.simplefilter(action="ignore", category=FutureWarning)

from inventario.repositories.movimiento_repo import MovimientoRepo

def _obtener_movimientos_df(taller_id: int) -> pd.DataFrame:

    repo = MovimientoRepo()
    qs = repo.get_egresos_ultimos_5_anios(taller_id=taller_id)
    df = pd.DataFrame(list(qs))

    if df.empty:
        raise ValueError(f"No se encontraron movimientos de EGRESO para el taller_id={taller_id}.")

    df = df.rename(
        columns={
            "numero_pieza": "NumeroParte",
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
    df["NumeroParte"] = df["NumeroParte"].astype(str)

    # Semana = lunes como inicio
    df["fecha"] = df["Fecha"].dt.to_period("W").apply(lambda r: r.start_time)
    df["fecha"] = pd.to_datetime(df["fecha"])

    # Agregación semanal por SKU
    demanda_semanal = (
        df.groupby(["NumeroParte", "fecha"], as_index=False)["Cantidad"].sum()
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
    demanda_semanal["NumeroParte"] = demanda_semanal["NumeroParte"].astype(str)

    primeras_fechas = demanda_semanal.groupby("NumeroParte")["fecha"].min()
    fecha_final = demanda_semanal["fecha"].max()

    full_list: List[pd.DataFrame] = []
    for sku in demanda_semanal["NumeroParte"].unique():
        fechas_sku = pd.date_range(start=primeras_fechas[sku], end=fecha_final, freq="W-MON")
        df_temp = pd.DataFrame({"NumeroParte": sku, "fecha": fechas_sku})
        full_list.append(df_temp)

    df_full = pd.concat(full_list, ignore_index=True)
    df_full = df_full.merge(demanda_semanal, on=["NumeroParte", "fecha"], how="left").fillna(0)

    volumen_historico = (
        df_full.groupby("NumeroParte")
        .agg(
            volumen_total=("Cantidad", "sum"),
            semanas_con_venta=("Cantidad", lambda x: (x > 0).sum()),
            total_semanas_registradas=("fecha", "count"),
        )
        .reset_index()
    )
    volumen_historico["intermitencia"] = 1 - (
        volumen_historico["semanas_con_venta"] / volumen_historico["total_semanas_registradas"]
    )

    def segmento_demanda(row):
        if row["volumen_total"] == 0:
            return "sin_venta"
        elif row["total_semanas_registradas"] < 26:
            return "nuevo"
        elif row["intermitencia"] >= 0.75: # o sea que si vendio el 25% de las semanas es frecuencia alta
            return "intermitente"
        else:
            return "frecuencia_alta"

    volumen_historico["segmento_demanda"] = volumen_historico.apply(segmento_demanda, axis=1)
    df_full = df_full.merge(
        volumen_historico[["NumeroParte", "segmento_demanda"]],
        on="NumeroParte",
        how="left",
    )

    print("Distribución de segmentos generada:")
    print(volumen_historico["segmento_demanda"].value_counts(normalize=True))

    return df_full

def generar_caracteristicas(df_full: pd.DataFrame) -> pd.DataFrame:
    """
    Genera variables de calendario, feriados, lags y rolling stats por segmento.
    """
    print("\n--- PASO 3: INGENIERÍA DE CARACTERÍSTICAS POR SEGMENTO ---")

    if df_full.empty:
        raise ValueError("df_full está vacío.")

    df_full = df_full.copy()
    df_full["fecha"] = pd.to_datetime(df_full["fecha"])

    ar_holidays = holidays.AR(
        years=np.arange(df_full["fecha"].dt.year.min(), df_full["fecha"].dt.year.max() + 2)
    )
    fechas_feriados = sorted(list(ar_holidays.keys()))
    feriados_semana = {pd.Timestamp(fecha).to_period("W").start_time for fecha in fechas_feriados}

    def dias_hasta_feriado(fecha: pd.Timestamp) -> int:
        proximos_feriados = [f for f in fechas_feriados if f > fecha.date()]
        if not proximos_feriados:
            return 365
        return (proximos_feriados[0] - fecha.date()).days

    def generar_features_por_segmento(df_segment: pd.DataFrame) -> pd.DataFrame:
        segmento = df_segment["segmento_demanda"].iloc[0]
        df_s = df_segment.copy().sort_values(["NumeroParte", "fecha"])

        print(f"Procesando características para segmento: '{segmento}'")

        # Dummies de mes
        df_s["mes"] = df_s["fecha"].dt.month
        mes_dummies = pd.get_dummies(df_s["mes"], prefix="mes", dtype=int)
        df_s = pd.concat([df_s, mes_dummies], axis=1).drop(columns=["mes"])

        # Dummies de semana del año
        df_s["semana_anio"] = df_s["fecha"].dt.isocalendar().week.astype(int)
        semana_dummies = pd.get_dummies(df_s["semana_anio"], prefix="semana", dtype=int)
        df_s = pd.concat([df_s, semana_dummies], axis=1).drop(columns=["semana_anio"])

        # Dummies de trimestre
        df_s["trimestre"] = df_s["fecha"].dt.quarter
        trimestre_dummies = pd.get_dummies(df_s["trimestre"], prefix="trimestre", dtype=int)
        df_s = pd.concat([df_s, trimestre_dummies], axis=1).drop(columns=["trimestre"])

        # Feriados y ventas
        df_s["es_semana_feriado"] = df_s["fecha"].isin(feriados_semana).astype(int)
        df_s["hubo_venta"] = (df_s["Cantidad"] > 0).astype(int)
        df_s["dias_hasta_feriado"] = df_s["fecha"].apply(dias_hasta_feriado)

        # Config por segmento
        if segmento == "frecuencia_alta":
            max_lag = 52
            windows = [4, 8, 12, 26, 52]
            lags_to_generate = list(range(1, max_lag + 1))
        elif segmento == "intermitente":
            max_lag = 12
            windows = [4, 8, 12]
            lags_to_generate = list(range(1, max_lag + 1))
        else:  # 'nuevo' (y 'sin_venta' no se usa para entrenar)
            windows = []
            lags_to_generate = []

        # Lags de ventas
        for lag in lags_to_generate:
            df_s[f"ventas_t_{lag}"] = df_s.groupby("NumeroParte")["Cantidad"].shift(lag)

        # Rolling stats sobre Cantidad (shift(1) para evitar fuga de info)
        for window in windows:
            rolling_series = df_s.groupby("NumeroParte")["Cantidad"].shift(1).rolling(window, min_periods=2)
            df_s[f"media_ultimas_{window}"] = rolling_series.mean()
            df_s[f"std_pasada_{window}_semanas"] = rolling_series.std()
            mean_col = f"media_ultimas_{window}"
            std_col = f"std_pasada_{window}_semanas"
            coef_var_col = f"coef_var_{window}"
            df_s[coef_var_col] = df_s[std_col] / (df_s[mean_col].replace(0, 1e-6) + 1e-6)

        return df_s

    dataframes_procesados = [
        generar_features_por_segmento(df_segmento)
        for _, df_segmento in df_full.groupby("segmento_demanda", dropna=False)
    ]
    df_modelo = pd.concat(dataframes_procesados, ignore_index=True)
    df_modelo = df_modelo.sort_values(["NumeroParte", "fecha"]).reset_index(drop=True)
    return df_modelo


def integrar_datos_externos(df_full: pd.DataFrame) -> pd.DataFrame:
    """
    Obtiene datos externos desde las funciones helper, calcula features
    (lags, EMAs, deltas) y los integra al DataFrame principal.
    """
    print("\n--- Integrando datos externos desde las funciones helper ---")

    df_full_con_externos = df_full.copy()
    df_full_con_externos["fecha"] = pd.to_datetime(df_full_con_externos["fecha"])

    modelos_externos = [
        {"function": obtener_todas_las_inflaciones, "nombre": "inflacion", "tipo": "mensual"},
        {"function": obtener_todos_los_patentamientos, "nombre": "patentamientos", "tipo": "anual"},
        {"function": obtener_todos_los_ipsa, "nombre": "ipsa", "tipo": "mensual"},
        {"function": obtener_todas_las_prendas, "nombre": "prenda", "tipo": "mensual"},
        {"function": obtener_todas_las_tasas_interes, "nombre": "tasa_de_interes", "tipo": "mensual"},
        {"function": obtener_todos_los_tipos_cambio, "nombre": "tipo_de_cambio", "tipo": "mensual"},
    ]

    for config in modelos_externos:
        helper_function = config["function"]
        new_col_name = config["nombre"]
        print(f" - Procesando: {helper_function.__name__}...")

        try:
            # --- 2. Extraer datos del modelo usando la función helper ---
            data_list = helper_function()
            if not data_list:
                warnings.warn(f"No se encontraron datos usando la función '{helper_function.__name__}'. Se omite.")
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

            # --- 3. Generar Características (Lags, EMAs, Deltas) ---
            if config["tipo"] == "anual":
                lags = [12, 24, 36]
                ema_spans = [12, 24]
            else:
                lags = [1, 2, 3, 6]
                ema_spans = [3, 6, 12]

            # Generate lagged features using a simple shift based on the index,
            # as the DataFrame is already sorted by date.
            for lag in lags:
                df_ext[f"{new_col_name}_lag_{lag}"] = df_ext[new_col_name].shift(lag)
            for span in ema_spans:
                df_ext[f"{new_col_name}_ema_{span}"] = df_ext[new_col_name].ewm(span=span, adjust=False).mean()
            df_ext[f"{new_col_name}_delta"] = df_ext[new_col_name].diff()

            # --- 4. Fusionar con el DataFrame principal ---
            df_ext_to_merge = df_ext.drop(columns=[new_col_name])
            df_full_con_externos = pd.merge_asof(
                df_full_con_externos.sort_values("fecha"),
                df_ext_to_merge.sort_values("fecha"),
                on="fecha",
                direction="backward",
            )
        except Exception as e:
            warnings.warn(f"Error procesando la función '{helper_function.__name__}': {e}. Se omite.")
            continue

    cols_nucleares = {"NumeroParte", "fecha", "Cantidad", "segmento_demanda"}
    cols_a_propagar = [col for col in df_full_con_externos.columns if col not in cols_nucleares]

    if cols_a_propagar:
        df_full_con_externos[cols_a_propagar] = df_full_con_externos.groupby("NumeroParte")[cols_a_propagar].ffill()

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.expand_frame_repr', False)
    print(df_full_con_externos.head())
    print("✓ Integración de datos externos completada.")
    return df_full_con_externos

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
    demanda_semanal = cargar_y_limpiar_datos_desde_repo(taller_id)
    if demanda_semanal.empty:
        raise ValueError("No hay datos de demanda semanal.")

    # 2) Clasificar
    df_full = clasificar_demanda(demanda_semanal)

    # 3) Externos
    df_full = integrar_datos_externos(df_full)

    # 4) Features
    df_modelo = generar_caracteristicas(df_full)

    # 5) Split + guardado por segmento (excepto 'sin_venta' y 'nuevo')
    print("\n--- PASO 4: DIVIDIENDO DATOS Y GUARDANDO EN CARPETAS POR SEGMENTO ---")
    resultados: Dict[str, Dict[str, pd.DataFrame]] = {}

    for segmento, df_segmento in df_modelo.groupby("segmento_demanda", dropna=False):
        ruta_segmento = os.path.join(output_dir_base,str(taller_id), segmento)
        os.makedirs(ruta_segmento, exist_ok=True)

        # Segmentos que no se entrenan
        if segmento in ["sin_venta", "nuevo"]:
            continue

        try:
            split_data = dividir_datos(df_segmento)
            resultados[segmento] = split_data

            # Guarda csv
            for part_name, part_df in split_data.items():
                nombre_archivo = f"demanda_preprocesada_{segmento}_{part_name}.csv"
                ruta_guardado = os.path.join(ruta_segmento, nombre_archivo)
                part_df.to_csv(ruta_guardado, index=False)
                print(
                    f"Segmento '{segmento}' ({part_name}) guardado en '{ruta_guardado}' "
                    f"con {part_df.shape[0]} filas."
                )
        except ValueError as e:
            print(f"Advertencia: No se pudo dividir el segmento '{segmento}': {e}")
            continue

    print("\n--- PROCESO COMPLETADO ---")
    return resultados


if __name__ == "__main__":
    # parametros para probar
    TALLER_ID = 1
    OUTPUT_DIR = "models" # donde se guardan los modelos

    ejecutar_preproceso(
        taller_id=TALLER_ID,
        output_dir_base=OUTPUT_DIR,
    )
