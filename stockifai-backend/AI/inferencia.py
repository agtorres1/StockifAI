# inferencia.py
# -*- coding: utf-8 -*-

import os
import warnings

import joblib
import numpy as np
import pandas as pd
import holidays

from catalogo.models import Repuesto
from d_externo.repositories.dataexterna import obtener_registroentrenamiento_intermitente, \
    obtener_registroentrenamiento_frecuencia_alta
from inventario.repositories.repuesto_taller_repo import RepuestoTallerRepo
from user.models import Taller

# --- Configuración de Django (si es necesario para los repositorios) ---
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockifai.settings')
# django.setup()

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)


# Directorio donde se guardaron los modelos entrenados
RUTA_BASE_MODELOS = "models"


def get_features_for_segment(segmento: str, df_columns: list) -> list:
    """
    Define y filtra la lista de features para cada segmento de demanda.
    Esta función debe ser IDÉNTICA a la del script de entrenamiento.
    """
    features_base = ['es_semana_feriado', 'dias_hasta_feriado']
    features_mes = [f'mes_{i}' for i in range(1, 13)]
    features_semana = [f'semana_{i}' for i in range(1, 53)]
    features_trimestre = [f'trimestre_{i}' for i in range(1, 4)]
    features_externas = [c for c in df_columns if any(c.startswith(prefix) for prefix in [
        'Inflacion', 'Ipsa', 'Patentamientos', 'Prendas', 'Tasa_de_interes_de_prestamos', 'Tipo_de_cambio'
    ]) and not c.endswith('_original')]

    if segmento == 'frecuencia_alta':
        features_lags = [f'ventas_t_{i}' for i in range(1, 53)]
        features_rolling = [f'media_ultimas_{i}' for i in [4, 8, 12, 26, 52]] + \
                           [f'std_pasada_{i}_semanas' for i in [4, 8, 12, 26, 52]] + \
                           [f'coef_var_{i}' for i in [4, 8, 12, 26, 52]]
        all_possible_features = features_base + features_externas + features_mes + features_semana + features_trimestre + features_lags + features_rolling

    elif segmento == 'intermitente':
        features_lags = [f'ventas_t_{i}' for i in range(1, 29)]
        features_rolling = [f'media_ultimas_{i}' for i in [4, 8, 12, 26, 52]] + \
                           [f'std_pasada_{i}_semanas' for i in [4, 8, 12, 26, 52]] + \
                           [f'coef_var_{i}' for i in [4, 8, 12, 26, 52]]
        all_possible_features = features_base + features_externas + features_mes + features_semana + features_trimestre + features_lags + features_rolling
    else:
        return []

    final_features = [col for col in all_possible_features if col in df_columns]
    return final_features


def generar_features_futuras(df_historia: pd.DataFrame, fecha_a_predecir: pd.Timestamp,
                             ar_holidays: holidays.HolidayBase) -> pd.DataFrame:
    """
    Genera las características para una única fecha futura, basándose en el historial.
    """
    df_historia = df_historia.sort_values("fecha").reset_index(drop=True)
    nuevo_registro = pd.DataFrame([{'fecha': fecha_a_predecir}])

    # 1. Características de calendario
    fechas_feriados = sorted(list(ar_holidays.keys()))
    feriados_semana = {pd.Timestamp(fecha).to_period("W").start_time for fecha in fechas_feriados}

    nuevo_registro["mes"] = nuevo_registro["fecha"].dt.month
    nuevo_registro["semana_anio"] = nuevo_registro["fecha"].dt.isocalendar().week.astype(int)
    nuevo_registro["trimestre"] = nuevo_registro["fecha"].dt.quarter

    for i in range(1, 13): nuevo_registro[f'mes_{i}'] = int(nuevo_registro['mes'] == i)
    for i in range(1, 53): nuevo_registro[f'semana_{i}'] = int(nuevo_registro['semana_anio'] == i)
    for i in range(1, 5): nuevo_registro[f'trimestre_{i}'] = int(nuevo_registro['trimestre'] == i)

    nuevo_registro["es_semana_feriado"] = nuevo_registro["fecha"].isin(feriados_semana).astype(int)

    proximos_feriados = [f for f in fechas_feriados if f > fecha_a_predecir.date()]
    nuevo_registro["dias_hasta_feriado"] = (
                proximos_feriados[0] - fecha_a_predecir.date()).days if proximos_feriados else 365

    # 2. Lags y Rolling Stats
    # Se concatenan temporalmente para calcular lags y rolling stats
    historia_combinada = pd.concat([df_historia, nuevo_registro[['fecha']]], ignore_index=True)
    historia_combinada = historia_combinada.sort_values("fecha").reset_index(drop=True)

    segmento = df_historia['segmento_demanda'].iloc[0]

    # Config por segmento
    lags_to_generate, windows = [], []
    if segmento == "frecuencia_alta":
        lags_to_generate = list(range(1, 53))
        windows = [4, 8, 12, 26, 52]
    elif segmento == "intermitente":
        lags_to_generate = list(range(1, 29))
        windows = [4, 8, 12]

    # Lags
    for lag in lags_to_generate:
        historia_combinada[f"ventas_t_{lag}"] = historia_combinada["Cantidad"].shift(lag)

    # Rolling stats
    for window in windows:
        rolling_series = historia_combinada["Cantidad"].shift(1).rolling(window, min_periods=2)
        historia_combinada[f"media_ultimas_{window}"] = rolling_series.mean()
        historia_combinada[f"std_pasada_{window}_semanas"] = rolling_series.std()

        mean_col = f"media_ultimas_{window}"
        std_col = f"std_pasada_{window}_semanas"
        coef_var_col = f"coef_var_{window}"

        # Evitar división por cero
        mean_val = historia_combinada[mean_col].replace(0, 1e-6) + 1e-6
        historia_combinada[coef_var_col] = historia_combinada[std_col] / mean_val

    # 3. Datos Externos (se propagan desde el último valor conocido)
    cols_externas = [c for c in df_historia.columns if any(c.startswith(prefix) for prefix in
                                                           ['Inflacion', 'Ipsa', 'Patentamientos', 'Prendas',
                                                            'Tasa_de_interes_de_prestamos', 'Tipo_de_cambio'])]

    ultimo_registro_externo = df_historia[cols_externas].iloc[-1]
    for col in cols_externas:
        historia_combinada.loc[historia_combinada.index[-1], col] = ultimo_registro_externo[col]

    # Devolvemos solo la última fila, que contiene los features para la fecha a predecir
    return historia_combinada.iloc[[-1]]


def guardar_predicciones_db(taller_id: int, predicciones: list):
    """
    Guarda las predicciones usando RepuestoTallerRepo.
    """
    try:
        taller = Taller.objects.get(id=taller_id)
    except Taller.DoesNotExist:
        print(f"No se encontró un Taller con id={taller_id}")
        return

    if not predicciones:
        print("No hay predicciones para guardar.")
        return

    repo = RepuestoTallerRepo()

    for pred in predicciones:
        numero_parte = pred.get("NumeroParte")
        if not numero_parte:
            continue
        try:
            repuesto = Repuesto.objects.get(numero_parte=numero_parte)
            resultado = repo.get_or_create(repuesto, taller)
            obj = resultado.obj

            for semana in range(1, 5):
                key = f'pred_semana_{semana}'
                if key in pred:
                    setattr(obj, f'pred_{semana}', pred[key])

            obj.save()
            print(f"Predicciones guardadas para SKU {numero_parte}")

        except Repuesto.DoesNotExist:
            print(f"Repuesto con numero_parte={numero_parte} no encontrado.")


def ejecutar_inferencia(taller_id: int, fecha_prediccion_str: str):
    print(f"\n--- INICIANDO PIPELINE DE INFERENCIA PARA TALLER ID: {taller_id} ---")
    print(f"Fecha de inicio de predicción: {fecha_prediccion_str}")

    # --- 1. Cargar el último registro de cada SKU desde Django ---
    registros_frecuencia_alta = obtener_registroentrenamiento_frecuencia_alta(taller_id)
    registros_intermitente = obtener_registroentrenamiento_intermitente(taller_id)

    # Convertir a DataFrame
    df_frecuencia_alta = pd.DataFrame(registros_frecuencia_alta)
    df_intermitente = pd.DataFrame(registros_intermitente)

    # Concatenar todos los registros
    df_ultimos_registros = pd.concat([df_frecuencia_alta, df_intermitente], ignore_index=True)
    if df_ultimos_registros.empty:
        print(f"No se encontraron registros para el taller_id={taller_id}.")
        return

    # Convertir columna fecha a datetime
    df_ultimos_registros['fecha'] = pd.to_datetime(df_ultimos_registros['fecha'])

    print(f"Se cargaron los últimos registros de {df_ultimos_registros['numero_parte'].nunique()} SKUs.")

    # Definir las 4 semanas futuras para la predicción
    fecha_inicio = pd.to_datetime(fecha_prediccion_str)
    fechas_a_predecir = pd.date_range(start=fecha_inicio, periods=4, freq='W-MON')

    # Feriados de Argentina
    ar_holidays = holidays.AR(years=np.arange(fecha_inicio.year, fecha_inicio.year + 2))

    resultados_finales = []

    for sku in df_ultimos_registros['numero_parte'].unique():
        historia_sku = df_ultimos_registros[df_ultimos_registros['numero_parte'] == sku].copy()
        segmento = historia_sku['segmento_demanda'].iloc[0]

        if segmento in ['sin_venta', 'nuevo']:
            print(f"SKU {sku} pertenece al segmento '{segmento}', se omite predicción.")
            continue

        # Cargar el modelo correspondiente
        ruta_modelo = os.path.join(RUTA_BASE_MODELOS, str(taller_id), segmento, f"modelo_lightgbm_{segmento}_final.pkl")
        if not os.path.exists(ruta_modelo):
            print(f"Advertencia: No se encontró el modelo para el segmento '{segmento}'. Se omite SKU {sku}.")
            continue

        modelo = joblib.load(ruta_modelo)
        features_del_modelo = modelo.feature_name_

        print(f"\nProcesando SKU: {sku} (Segmento: {segmento})")
        predicciones_sku = {'NumeroParte': sku}
        historia_temporal = historia_sku.copy()

        for i, fecha_futura in enumerate(fechas_a_predecir):
            features_para_predecir_df = generar_features_futuras(historia_temporal, fecha_futura, ar_holidays)
            features_para_predecir_df = features_para_predecir_df[features_del_modelo]
            prediccion_raw = modelo.predict(features_para_predecir_df)
            prediccion_final = np.maximum(0, prediccion_raw).round().astype(int)[0]

            print(f"  - Predicción para {fecha_futura.date()} (Semana {i + 1}): {prediccion_final}")
            predicciones_sku[f'pred_semana_{i + 1}'] = prediccion_final

            nuevo_registro_predicho = features_para_predecir_df.copy()
            nuevo_registro_predicho['fecha'] = fecha_futura
            nuevo_registro_predicho['Cantidad'] = prediccion_final
            nuevo_registro_predicho['numero_parte'] = sku
            nuevo_registro_predicho['segmento_demanda'] = segmento

            historia_temporal = pd.concat([historia_temporal, nuevo_registro_predicho], ignore_index=True)

        resultados_finales.append(predicciones_sku)

    if resultados_finales:
        print("\n--- Guardando predicciones en la base de datos ---")
        guardar_predicciones_db(taller_id, resultados_finales)


    else:
        print("\nNo se generaron predicciones.")

    print("\n--- PROCESO DE INFERENCIA COMPLETADO ---")


if __name__ == '__main__':
    # --- Parámetros de ejecución ---
    TALLER_A_PREDECIR = 1
    # La fecha debe ser un lunes, que es el inicio de la semana según el preproceso.
    FECHA_INICIO_PREDICCION = "2025-07-07"

    ejecutar_inferencia(
        taller_id=TALLER_A_PREDECIR,
        fecha_prediccion_str=FECHA_INICIO_PREDICCION
    )