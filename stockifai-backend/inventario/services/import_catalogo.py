# inventario/services/import_catalogo.py
from django.db import transaction
from django.db.models import Q
import pandas as pd

from catalogo.models import Repuesto, Categoria, Marca
from ..repositories.base import NotFoundError
from ._helpers_movimientos import read_df
from ._helpers_catalogo import norm_cols_catalogo

from ..repositories.repuesto_repo import RepuestoRepo
from ..repositories.categoria_repo import CategoriaRepo
from ..repositories.marca_repo import MarcaRepo

repuesto_repo = RepuestoRepo()
categoria_repo = CategoriaRepo()
marca_repo = MarcaRepo()

_VALID_ESTADOS = {"ACTIVO", "INACTIVO"}
BULK_CHUNK = 2000  # ajustá 1000–5000 según memoria/DB

def _is_na(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and v.strip() == "")

def _norm_estado(v: str, default_estado: str) -> str:
    v = "" if v is None else str(v).strip().upper()
    return v if v in _VALID_ESTADOS else default_estado

def _resolver_categoria(row, categorias_by_id, categorias_by_name, categoria_repo):
    # por id
    if "categoria_id" in row and not _is_na(row["categoria_id"]):
        try:
            cid = int(row["categoria_id"])
            if cid in categorias_by_id:
                return categorias_by_id[cid]
        except Exception:
            pass
    # por nombre
    if "categoria" in row and not _is_na(row["categoria"]):
        nombre = str(row["categoria"]).strip()
        if nombre:
            if nombre in categorias_by_name:
                return categorias_by_name[nombre]
            created = categoria_repo.get_or_create(nombre).obj
            if getattr(created, "id", None):
                categorias_by_id[created.id] = created
                categorias_by_name[nombre] = created
            return created
    return None

def _resolver_marca(row, marcas_by_id, marcas_by_name, marca_repo):
    if "marca_id" in row and not _is_na(row["marca_id"]):
        try:
            mid = int(row["marca_id"])
            if mid in marcas_by_id:
                return marcas_by_id[mid]
        except Exception:
            pass
    if "marca" in row and not _is_na(row["marca"]):
        nombre = str(row["marca"]).strip()
        if nombre:
            if nombre in marcas_by_name:
                return marcas_by_name[nombre]
            created = marca_repo.get_or_create(nombre).obj
            if getattr(created, "id", None):
                marcas_by_id[created.id] = created
                marcas_by_name[nombre] = created
            return created
    return None

def _fetch_categorias_y_marca(df: pd.DataFrame):
    cat_ids, cat_names, mar_ids, mar_names = set(), set(), set(), set()

    if "categoria_id" in df.columns:
        for v in df["categoria_id"]:
            if not _is_na(v):
                try:
                    cat_ids.add(int(v))
                except Exception:
                    pass
    if "categoria" in df.columns:
        cat_names = {s for s in (str(x).strip() for x in df["categoria"].dropna()) if s}

    if "marca_id" in df.columns:
        for v in df["marca_id"]:
            if not _is_na(v):
                try:
                    mar_ids.add(int(v))
                except Exception:
                    pass
    if "marca" in df.columns:
        mar_names = {s for s in (str(x).strip() for x in df["marca"].dropna()) if s}

    categorias = list(Categoria.objects.filter(Q(id__in=cat_ids) | Q(nombre__in=cat_names)).only("id", "nombre"))
    marcas = list(Marca.objects.filter(Q(id__in=mar_ids) | Q(nombre__in=mar_names)).only("id", "nombre"))

    categorias_by_id = {c.id: c for c in categorias}
    categorias_by_name = {c.nombre: c for c in categorias}
    marcas_by_id = {m.id: m for m in marcas}
    marcas_by_name = {m.nombre: m for m in marcas}

    return categorias_by_id, categorias_by_name, marcas_by_id, marcas_by_name

def importar_catalogo(*, file, fields_map: dict | None = None,
                      default_estado: str = "ACTIVO",
                      mode: str = "upsert"):
    """
    Importa catálogo de repuestos.
    Requeridos por fila: numero_pieza, descripcion
    Opcionales: estado, categoria_id|categoria, marca_id|marca
    mode: upsert | create-only | update-only
    """
    df = read_df(file)
    df = norm_cols_catalogo(df, fields_map or {})

    # normalización básica
    df["numero_pieza"] = df["numero_pieza"].astype(str).str.strip()
    df["descripcion"] = df["descripcion"].astype(str).str.strip()
    df = df[~df["numero_pieza"].astype(str).str.fullmatch(r"\s*")]  # filtra vacíos reales
    df = df.drop_duplicates(subset=["numero_pieza"])

    if "estado" not in df.columns:
        df["estado"] = default_estado
    df["estado"] = df["estado"].apply(lambda v: _norm_estado(v, default_estado))

    # Prefetch existencias fuera del loop
    numeros = df["numero_pieza"].tolist()
    existentes_qs = (
        Repuesto.objects.filter(numero_pieza__in=numeros)
        .only("id", "numero_pieza", "descripcion", "estado", "categoria_id", "marca_id")
    )
    existentes = {r.numero_pieza: r for r in existentes_qs}

    creados = actualizados = ignorados = 0
    errores = []

    categorias_by_id, categorias_by_name, marcas_by_id, marcas_by_name = _fetch_categorias_y_marca(df)

    # Procesar por CHUNKS con transacciones acotadas
    rows = df.to_dict("records")
    for i in range(0, len(rows), BULK_CHUNK):
        chunk = rows[i:i + BULK_CHUNK]
        # colecciones para bulk_update (más rápido que save() por ítem)
        to_update = []
        with transaction.atomic():
            for idx, row in enumerate(chunk, start=i):
                try:
                    numero = row.get("numero_pieza", "").strip()
                    descripcion = row.get("descripcion", "").strip()
                    if not numero or not descripcion:
                        raise ValueError("Las columnas 'numero_pieza' y 'descripcion' son obligatorias.")

                    categoria = _resolver_categoria(row, categorias_by_id, categorias_by_name, categoria_repo)
                    marca = _resolver_marca(row, marcas_by_id, marcas_by_name, marca_repo)

                    rep = existentes.get(numero)
                    existe = rep is not None

                    if existe and mode == "create-only":
                        ignorados += 1
                        continue
                    if not existe and mode == "update-only":
                        ignorados += 1
                        continue

                    if existe:
                        # detectar cambios en campos REALES
                        changed = False
                        if rep.descripcion != descripcion:
                            rep.descripcion = descripcion; changed = True
                        if rep.estado != row.get("estado"):
                            rep.estado = row.get("estado"); changed = True
                        if categoria is not None and rep.categoria_id != getattr(categoria, "id", None):
                            rep.categoria = categoria; changed = True
                        if marca is not None and rep.marca_id != getattr(marca, "id", None):
                            rep.marca = marca; changed = True

                        if changed:
                            to_update.append(rep)
                        else:
                            ignorados += 1
                    else:
                        # crear vía repo (si tu repo ya optimiza/valida)
                        rep = repuesto_repo.create(
                            numero_pieza=numero,
                            descripcion=descripcion,
                            estado=row.get("estado"),
                            categoria=categoria,
                            marca=marca,
                        )
                        existentes[numero] = rep
                        creados += 1

                except Exception as ex:
                    # +2 si tu CSV tiene encabezado
                    errores.append({"fila": int(idx) + 2, "motivo": str(ex)})

            # flush del update masivo del chunk
            if to_update:
                # si necesitás performance máxima, podés pasar update_fields explícitos
                Repuesto.objects.bulk_update(
                    to_update,
                    fields=["descripcion", "estado", "categoria", "marca"],
                    batch_size=BULK_CHUNK
                )
                actualizados += len(to_update)

    return {
        "creados": creados,
        "actualizados": actualizados,
        "ignorados": ignorados,
        "rechazados": len(errores),
        "errores": errores,
        "mode": mode,
        "default_estado": default_estado,
    }
