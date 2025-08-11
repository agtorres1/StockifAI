import re, unicodedata
import pandas as pd
from datetime import datetime
from django.utils.timezone import make_aware

def read_df(file) -> pd.DataFrame:
    name = getattr(file, 'name', '').lower()
    if name.endswith('.csv'):
        return pd.read_csv(file)
    return pd.read_excel(file)

# --- normalización de encabezados (auto-mapeo con sinónimos) ---
def _slug(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '', s.lower())

_SYNS = {
    'fecha': {'fecha','fechamov','fmov','foper','fechaoper','fechaoperacion','date','fechahora'},
    'tipo': {'tipo','mov','movimiento','oper','operacion','io','ingresoegreso','entradaegreso'},
    'cantidad': {'cantidad','cant','qty','unidades','q'},
    'numero_pieza': {'repuesto','pn','sku','codigo','codigopieza','partnumber','numeropieza','nropieza','pieza'},
    'externo_id': {'kardexid','id','idexterno','referencia','nro','numero','comprobante'},
    'deposito': {'deposito','depositos','depositoalmacen','almacen','bodega','deposito1','depósito'},
    'documento': {'documento','doc','remito','factura','comprobante','nrocomprobante'},
}
_REQ = {'fecha','tipo','cantidad','numero_pieza'}

def norm_cols(df: pd.DataFrame, fields_map: dict | None) -> pd.DataFrame:
    # 1) aplicar mapping opcional si vino desde el front
    if fields_map:
        inv = {v: k for k, v in fields_map.items() if v in df.columns}
        if inv:
            df = df.rename(columns=inv)

    # 2) auto-mapeo por sinónimos (case/tildes/espacios)
    ren = {}
    for col in df.columns:
        slug = _slug(col)
        for std, syns in _SYNS.items():
            if slug == std or slug in syns:
                ren[col] = std
                break
    if ren:
        df = df.rename(columns=ren)

    # 3) validar requeridos
    missing = _REQ - set(df.columns)
    if missing:
        found = ", ".join(map(str, df.columns))
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}. Encabezados detectados: {found}")
    return df
# ----------------------------------------------------------------

def parse_fecha(val):
    if isinstance(val, datetime):
        return make_aware(val) if val.tzinfo is None else val
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d/%m/%Y %H:%M:%S","%Y-%m-%d %H:%M:%S"):
        try:
            return make_aware(datetime.strptime(str(val), fmt))
        except Exception:
            pass
    raise ValueError(f"Fecha inválida: {val}")

def norm_tipo(v: str) -> str:
    v = str(v).strip().upper()
    mapa = {
        "I":"INGRESO","INGRESO":"INGRESO","ENTRADA":"INGRESO",
        "E":"EGRESO","EGRESO":"EGRESO","SALIDA":"EGRESO",
        "AJUSTE+":"AJUSTE+","AJUSTE-":"AJUSTE-"
    }
    if v not in mapa:
        raise ValueError(f"Tipo inválido: {v}")
    return mapa[v]
