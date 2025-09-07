import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import warnings
from sqlalchemy import create_engine
from typing import Dict, Any, List

warnings.simplefilter(action='ignore', category=FutureWarning)


def get_features_for_segment(segmento: str, df_columns: list) -> list:
    """
    Define y filtra la lista de features para cada segmento de demanda.
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
        features_lags = []
        features_rolling = []
        all_possible_features = features_base + features_externas + features_mes + features_semana + features_trimestre

    final_features = [col for col in all_possible_features if col in df_columns]
    return final_features


def guardar_ultimo_registro_a_db(df: pd.DataFrame):

    print("\nIniciando la carga del último registro de cada SKU a la base de datos...")

    try:
        engine = create_engine(db_connection_string)

        # Obtenemos el último registro (última fecha) para cada SKU
        df_ultimo_registro = df.sort_values('fecha').drop_duplicates(subset=['NumeroParte'], keep='last')

        # Filtramos las columnas relevantes para la base de datos
        cols_to_save = [col for col in df_ultimo_registro.columns if col not in ['Cantidad', 'pred', 'error_abs']]
        df_ultimo_registro_db = df_ultimo_registro[cols_to_save]

        # Guardamos en la base de datos, usando 'replace' para actualizar los registros existentes
        df_ultimo_registro_db.to_sql(tabla_destino, engine, if_exists='replace', index=False)

        print(
            f"Últimos registros de {len(df_ultimo_registro_db)} SKUs guardados con éxito en la tabla '{tabla_destino}'.")
    except Exception as e:
        print(f"Error al guardar los últimos registros en la base de datos: {e}")


def train_segment_model(taller: int, segmento: str, ruta_base: str, db_connection_string: str):
    """
    Carga datos preprocesados y entrena un modelo LightGBM para un segmento específico.
    """
    ruta_segmento_data = os.path.join(ruta_base, str(taller), segmento)
    ruta_archivo_train = os.path.join(ruta_segmento_data, f"demanda_preprocesada_{segmento}_train.csv")
    ruta_archivo_val = os.path.join(ruta_segmento_data, f"demanda_preprocesada_{segmento}_val.csv")
    ruta_archivo_test = os.path.join(ruta_segmento_data, f"demanda_preprocesada_{segmento}_test.csv")

    if not os.path.isfile(ruta_archivo_train) or not os.path.isfile(ruta_archivo_val) or not os.path.isfile(
            ruta_archivo_test):
        print(f"Advertencia: No se encontraron todos los archivos de datos para el segmento '{segmento}'. Saltando.")
        return

    print(f"\n--- INICIANDO ENTRENAMIENTO PARA EL SEGMENTO: '{segmento.upper()}' ---")
    df_train = pd.read_csv(ruta_archivo_train)
    df_val = pd.read_csv(ruta_archivo_val)
    df_test = pd.read_csv(ruta_archivo_test)

    df_train['fecha'] = pd.to_datetime(df_train['fecha'])
    df_val['fecha'] = pd.to_datetime(df_val['fecha'])
    df_test['fecha'] = pd.to_datetime(df_test['fecha'])

    TARGET = 'Cantidad'
    features = get_features_for_segment(segmento, df_train.columns)

    if TARGET not in df_train.columns or not features:
        print(f"Error: No se encontraron las columnas necesarias en los archivos de datos para '{segmento}'.")
        return

    # Fase de Validación (Rolling Forecast)
    print("Iniciando fase de validación (rolling forecast)...")
    fechas_val_unicas = sorted(df_val['fecha'].unique())
    all_val_predictions = pd.DataFrame()

    if len(fechas_val_unicas) >= 4:
        for i in range(len(fechas_val_unicas)):
            current_fecha_val = fechas_val_unicas[i]

            df_train_temp = pd.concat([df_train, df_val[df_val['fecha'] < current_fecha_val]]).copy()
            df_test_temp = df_val[df_val['fecha'] == current_fecha_val].copy()

            X_train, y_train = df_train_temp[features], df_train_temp[TARGET]
            X_test, y_test = df_test_temp[features], df_test_temp[TARGET]

            if X_train.empty or X_test.empty:
                continue

            lgb_model_val = lgb.LGBMRegressor(
                objective='regression_l1',
                metric='mae',
                random_state=42,
                n_jobs=-1,
                learning_rate=0.05,
                n_estimators=1000,
                max_depth=8
            )

            lgb_model_val.fit(X_train, y_train,
                              eval_set=[(X_test, y_test)],
                              eval_metric='mae',
                              callbacks=[lgb.early_stopping(50, verbose=False)])

            y_pred_val = lgb_model_val.predict(X_test)
            y_pred_clipped = np.maximum(0, y_pred_val).round().astype(int)

            df_test_temp['pred'] = y_pred_clipped
            all_val_predictions = pd.concat([all_val_predictions, df_test_temp], ignore_index=True)

        print("Validación completada.")

    else:
        print("Advertencia: No hay suficientes semanas para la validación. Saltando la validación.")

    # Entrenamiento del modelo final con train + val
    print("\nEntrenando modelo final con todos los datos de train y val...")
    df_full_train = pd.concat([df_train, df_val]).copy()
    X_full_train, y_full_train = df_full_train[features], df_full_train[TARGET]

    lgb_final_model = lgb.LGBMRegressor(
        objective='regression_l1',
        metric='mae',
        random_state=42,
        n_jobs=-1,
        learning_rate=0.05,
        n_estimators=1000,
        max_depth=8
    )

    lgb_final_model.fit(X_full_train, y_full_train)

    # Predicción y evaluación en el conjunto de test
    print("\n--- PREDICCIÓN Y EVALUACIÓN EN EL CONJUNTO DE TEST ---")
    X_test, y_test = df_test[features], df_test[TARGET]
    y_pred_test = lgb_final_model.predict(X_test)
    y_pred_clipped_test = np.maximum(0, y_pred_test).round().astype(int)

    df_test['pred'] = y_pred_clipped_test
    df_test['error_abs'] = (df_test['Cantidad'] - df_test['pred']).abs()

    mae_final = mean_absolute_error(y_test, y_pred_clipped_test)
    rmse_final = np.sqrt(mean_squared_error(y_test, y_pred_clipped_test))

    print(f"Error Absoluto Medio (MAE) Final: {mae_final:.2f}")
    print(f"Raíz del Error Cuadrático Medio (RMSE) Final: {rmse_final:.2f}")

    # Guardar modelo final y resultados
    model_filename = f"modelo_lightgbm_{segmento}_final.pkl"
    ruta_guardado_modelo = os.path.join(ruta_segmento_data, model_filename)
    joblib.dump(lgb_final_model, ruta_guardado_modelo)
    print(f"Modelo final para '{segmento}' guardado en '{ruta_guardado_modelo}'.")

    guardar_ultimo_registro_a_db(df_test)


def ejecutar_pipeline_entrenamiento(taller_id: int, ruta_base: str = 'models', db_config: Dict[str, Any] = None):
    """
    Ejecuta el pipeline de entrenamiento para todos los segmentos de un taller.
    """
    if db_config is None:
        print("Error: No se proporcionó la configuración de la base de datos.")
        return

    db_connection_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"

    ruta_taller_output = os.path.join(ruta_base, str(taller_id))

    if not os.path.isdir(ruta_taller_output):
        print(f"Error: No se encontró la carpeta del taller en '{ruta_taller_output}'.")
        return

    segmentos = [d for d in os.listdir(ruta_taller_output) if
                 os.path.isdir(os.path.join(ruta_taller_output, d)) and d != 'validacion']

    if not segmentos:
        print(f"No se encontraron subcarpetas de segmentos en '{ruta_taller_output}'.")
        return

    for segmento in segmentos:
        if segmento in ['nuevo', 'sin_venta']:
            continue
        train_segment_model(taller_id, segmento, ruta_base, db_connection_string)

    print("\n--- PROCESO DE ENTRENAMIENTO COMPLETO ---")


if __name__ == '__main__':
    taller_id =  1
    ejecutar_pipeline_entrenamiento(taller_id, db_config=db_config_params)