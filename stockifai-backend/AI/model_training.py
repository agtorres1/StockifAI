import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import warnings
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockifai.settings')
django.setup()
from d_externo.models import RegistroEntrenamiento_Frecuencia_Alta

from d_externo.repositories.dataexterna import guardar_registroentrenamiento_frecuencia_alta, \
    guardar_registroentrenamiento_intermitente, borrar_registroentrenamiento_frecuencia_alta, \
    borrar_registroentrenamiento_intermitente
from user.models import Taller

warnings.simplefilter(action='ignore', category=FutureWarning)


RUTA_BASE_MODELOS = "models"

def get_features_for_segment(segmento: str, df_columns: list) -> list:
    """
    Define y filtra la lista de features para cada segmento de demanda.
    """
    features_base = ['es_semana_feriado', 'dias_hasta_feriado']
    features_mes = [f'mes_{i}' for i in range(1, 13)]
    features_semana = [f'semana_{i}' for i in range(1, 53)]
    features_trimestre = [f'trimestre_{i}' for i in range(1, 4)]
    features_externas = [c for c in df_columns if any(c.startswith(prefix) for prefix in [
        'Inflacion', 'Ipsa', 'Patentamientos', 'Prendas', 'Tasa_de_interes', 'Tipo_de_cambio'
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
        all_possible_features = features_base + features_externas + features_mes + features_semana + features_trimestre

    final_features = [col for col in all_possible_features if col in df_columns]
    return final_features


def guardar_ultimo_registro_a_db(df: pd.DataFrame, segmento: str, taller_id: int):
    """
    Guarda el último registro de cada SKU en la base de datos de Django
    usando los modelos correspondientes según el segmento.
    """
    taller = Taller.objects.get(id=taller_id)
    # --- LÓGICA DE BORRADO: Vaciar los registros previos antes de guardar los nuevos datos ---
    try:
        if segmento == "frecuencia_alta":
            borrar_registroentrenamiento_frecuencia_alta(taller)
        elif segmento == "intermitente":
            borrar_registroentrenamiento_intermitente(taller)
    except Exception as e:
        print(f"Advertencia: No se pudo borrar la tabla '{segmento}': {e}")

    print("\nIniciando la carga del último registro de cada SKU a la base de datos...")

    try:
        # Obtenemos el último registro (última fecha) para cada SKU
        df_ultimo_registro = df.sort_values('fecha').drop_duplicates(
            subset=['numero_pieza'], keep='last'
        )

        # Iteramos fila por fila y guardamos en el modelo correcto
        for _, row in df_ultimo_registro.iterrows():
            datos = row.to_dict()

            # Normalizamos nombres de columnas (coincidir con modelo Django)
            datos = {k.lower(): v for k, v in datos.items()}

            # --- CORRECCIÓN: Convertir NaN a None para MySQL ---
            for k, v in datos.items():
                if pd.isna(v):
                    datos[k] = None

            if segmento == "frecuencia_alta":
                guardar_registroentrenamiento_frecuencia_alta(datos, taller)
            elif segmento == "intermitente":
                guardar_registroentrenamiento_intermitente(datos, taller)
            else:
                print(f"Segmento '{segmento}' no soportado. Registro no guardado.")
                continue

        print(f"Últimos registros de {len(df_ultimo_registro)} SKUs guardados con éxito en '{segmento}'.")

    except Exception as e:
        print(f"Error al guardar los últimos registros en la base de datos: {e}")


def train_segment_model(taller: int, segmento: str):
    """
    Carga datos preprocesados y entrena un modelo LightGBM para un segmento específico.
    """
    ruta_segmento_data = os.path.join(RUTA_BASE_MODELOS, str(taller), segmento)
    ruta_archivo_train = os.path.join(ruta_segmento_data, f"demanda_preprocesada_{segmento}_train.csv")
    ruta_archivo_val = os.path.join(ruta_segmento_data, f"demanda_preprocesada_{segmento}_val.csv")
    ruta_archivo_test = os.path.join(ruta_segmento_data, f"demanda_preprocesada_{segmento}_test.csv")

    if not os.path.isfile(ruta_archivo_train) or not os.path.isfile(ruta_archivo_val) or not os.path.isfile(ruta_archivo_test):
        print(f"Advertencia: No se encontraron todos los archivos de datos para el segmento '{segmento}'. Saltando.")
        return

    try:
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

        # Validación (rolling forecast)
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
        else:
            print("Advertencia: No hay suficientes semanas para la validación. Saltando la validación.")

        # Entrenamiento final
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

        # Predicción en test
        X_test, y_test = df_test[features], df_test[TARGET]
        y_pred_test = lgb_final_model.predict(X_test)
        y_pred_clipped_test = np.maximum(0, y_pred_test).round().astype(int)

        mae_final = mean_absolute_error(y_test, y_pred_clipped_test)
        rmse_final = np.sqrt(mean_squared_error(y_test, y_pred_clipped_test))

        print(f"Error Absoluto Medio (MAE) Final: {mae_final:.2f}")
        print(f"Raíz del Error Cuadrático Medio (RMSE) Final: {rmse_final:.2f}")

        # Guardar modelo
        model_filename = f"modelo_lightgbm_{segmento}_final.pkl"
        ruta_guardado_modelo = os.path.join(ruta_segmento_data, model_filename)
        joblib.dump(lgb_final_model, ruta_guardado_modelo)
        print(f"Modelo final para '{segmento}' guardado en '{ruta_guardado_modelo}'.")

        # Guardar resultados en DB
        guardar_ultimo_registro_a_db(df_test, segmento, taller_id=taller)

    except Exception as e:
        print(f"Error durante el entrenamiento del segmento '{segmento}': {e}")
        return

    else:
        # Solo si  fue exitoso, eliminar archivos CSV
        for ruta in [ruta_archivo_train, ruta_archivo_val, ruta_archivo_test]:
            try:
                os.remove(ruta)
                print(f"Archivo '{ruta}' eliminado correctamente.")
            except Exception as e:
                print(f"No se pudo eliminar '{ruta}': {e}")


def ejecutar_pipeline_entrenamiento(taller_id: int):
    """
    Ejecuta el pipeline de entrenamiento para todos los segments de un taller.
    """

    ruta_taller_output = os.path.join(RUTA_BASE_MODELOS, str(taller_id))

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
        train_segment_model(taller_id, segmento)

    print("\n--- PROCESO DE ENTRENAMIENTO COMPLETO ---")


if __name__ == '__main__':
    taller_id =  1
    ejecutar_pipeline_entrenamiento(taller_id)