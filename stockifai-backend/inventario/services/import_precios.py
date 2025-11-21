from decimal import Decimal, InvalidOperation
from typing import Dict

import pandas as pd
from django.db import transaction

from catalogo.models import Repuesto, RepuestoTaller
from user.models import Taller

from ._helpers_movimientos import read_df


_REQUIRED_COLS = {"numero_pieza", "precio", "costo"}


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or (isinstance(value, str) and value.strip() == "")


def _norm_cols_precios(df: pd.DataFrame, fields_map: Dict[str, str] | None = None) -> pd.DataFrame:
    """Normaliza encabezados a las columnas esperadas para importación de precios."""
    if fields_map:
        df = df.rename(
            columns={
                fields_map[k]: k
                for k in _REQUIRED_COLS
                if k in fields_map and fields_map[k] in df.columns
            }
        )

    lower_map = {c.lower(): c for c in df.columns}
    ren = {}
    for k in _REQUIRED_COLS:
        if k in lower_map:
            ren[lower_map[k]] = k
    if ren:
        df = df.rename(columns=ren)

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(missing))}")

    return df


def _parse_decimal(raw, field_label: str) -> Decimal:
    if _is_empty(raw):
        raise ValueError(f"El {field_label} es obligatorio")

    value_str = str(raw).strip().replace(",", ".")
    try:
        value = Decimal(value_str)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_label.capitalize()} inválido: '{raw}'")

    return value.quantize(Decimal("0.01"))


@transaction.atomic
def importar_precios(*, file, taller_id: int, fields_map: dict | None = None):
    """
    Importa precios y costos para un taller desde un Excel/CSV con columnas:
    numero_pieza, precio, costo.
    """
    df = read_df(file)
    df = _norm_cols_precios(df, fields_map)

    df["numero_pieza"] = df["numero_pieza"].astype(str).str.strip()
    df = df[df["numero_pieza"] != ""]
    df = df.drop_duplicates(subset=["numero_pieza"], keep="last")

    taller = Taller.objects.filter(id=taller_id).first()
    if not taller:
        raise ValueError("Taller no encontrado")

    numeros = df["numero_pieza"].tolist()
    existentes = {r.numero_pieza: r for r in Repuesto.objects.filter(numero_pieza__in=numeros).only("id", "numero_pieza")}

    creados = actualizados = ignorados = rechazados = 0
    errores = []

    for idx, row in enumerate(df.to_dict("records")):
        try:
            numero = row.get("numero_pieza", "").strip()
            repuesto = existentes.get(numero)
            if not repuesto:
                raise ValueError("Repuesto no encontrado en catálogo")

            precio = _parse_decimal(row.get("precio"), "precio")
            costo = _parse_decimal(row.get("costo"), "costo")

            rt, created = RepuestoTaller.objects.get_or_create(
                repuesto=repuesto,
                taller=taller,
                defaults={"precio": precio, "costo": costo},
            )

            if created:
                creados += 1
                continue

            changed = False
            if rt.precio != precio:
                rt.precio = precio
                changed = True
            if rt.costo != costo:
                rt.costo = costo
                changed = True

            if changed:
                rt.save(update_fields=["precio", "costo"])
                actualizados += 1
            else:
                ignorados += 1
        except Exception as ex:  # noqa: BLE001
            errores.append({"fila": idx + 2, "motivo": str(ex)})
            rechazados += 1

    return {
        "creados": creados,
        "actualizados": actualizados,
        "ignorados": ignorados,
        "rechazados": rechazados,
        "errores": errores,
        "taller_id": taller_id,
        "total_recibidos": len(df),
    }