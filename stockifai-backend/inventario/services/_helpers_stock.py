# inventario/services/helpers_stock.py
import pandas as pd

def norm_cols_stock(df: pd.DataFrame, fields_map: dict | None = None) -> pd.DataFrame:
    """
    Normaliza encabezados a estándar para importación de STOCK.
    fields_map usa el esquema: {"numero_pieza": "repuesto_en_excel", "cantidad": "qty", "deposito": "dep", ...}
    """
    required = {"numero_pieza", "cantidad", "deposito"}

    # 1) Renombrar usando mapping estándar->archivo (solo si la columna existe en el archivo)
    if fields_map:
        df = df.rename(columns={ fields_map[k]: k for k in required if k in fields_map and fields_map[k] in df.columns })

    # 2) Normalizar por case-insensitive a los nombres estándar si ya existen en el archivo
    lower_map = {c.lower(): c for c in df.columns}
    ren = {}
    for k in required:
        if k in lower_map:  # misma palabra, distinto case
            ren[lower_map[k]] = k
    if ren:
        df = df.rename(columns=ren)

    # 3) Validar requeridas
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(missing))}")

    return df
