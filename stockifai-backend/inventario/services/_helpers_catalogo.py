# inventario/services/helpers_catalogo.py
import pandas as pd

def norm_cols_catalogo(df: pd.DataFrame, fields_map: dict | None = None) -> pd.DataFrame:
    """
    Normaliza encabezados a estándar para importación de CATÁLOGO.
    fields_map usa el esquema estándar->archivo, por ej:
      {
        "numero_pieza": "pn",
        "descripcion": "desc",
        "estado": "status",
        "categoria_id": "cat_id",
        "categoria_nombre": "categoria",
        "marca_id": "brand_id",
        "marca_nombre": "marca",
      }
    Requeridos: numero_pieza, descripcion
    """
    required = {"numero_pieza", "descripcion"}
    optional = {
        "estado", "categoria_id", "categoria_nombre",
        "marca_id", "marca_nombre"
    }
    all_keys = required | optional

    # 1) Renombrar según mapping (solo si existe la columna en el archivo)
    if fields_map:
        df = df.rename(columns={
            fields_map[k]: k
            for k in all_keys
            if k in fields_map and fields_map[k] in df.columns
        })

    # 2) Normalizar case-insensitive para claves estándar presentes tal cual
    lower_map = {c.lower(): c for c in df.columns}
    ren = {}
    for k in all_keys:
        if k in lower_map:  # misma palabra en otro case
            ren[lower_map[k]] = k
    if ren:
        df = df.rename(columns=ren)

    # 3) Validar requeridas
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(missing))}")

    return df
