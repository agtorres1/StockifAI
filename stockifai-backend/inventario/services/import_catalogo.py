# inventario/services/import_catalogo.py
from django.db import transaction
from django.db.models import Q

from catalogo.models import Repuesto, Categoria, Marca
from ..repositories.base import NotFoundError
from ._helpers_movimientos import read_df
from ._helpers_catalogo import norm_cols_catalogo

from ..repositories.repuesto_repo import RepuestoRepo

# Estos dos repos suponen métodos get(id), get_by_nombre(nombre),
# y get_or_create(nombre) -> obj con .obj como en tu patrón actual.
from ..repositories.categoria_repo import CategoriaRepo
from ..repositories.marca_repo import MarcaRepo

repuesto_repo = RepuestoRepo()
categoria_repo = CategoriaRepo()
marca_repo = MarcaRepo()

_VALID_ESTADOS = {"ACTIVO", "INACTIVO"}

def _norm_estado(v: str, default_estado: str) -> str:
    v = (str(v).strip().upper() if v is not None else "").upper()
    if v in _VALID_ESTADOS:
        return v
    return default_estado  # por defecto ACTIVO

def _resolver_categoria(row, categorias_by_id, categorias_by_name, categoria_repo):
    if "categoria_id" in row and row["categoria_id"] not in (None, "", float("nan")):
        try:
            cid = int(row["categoria_id"])
            if cid in categorias_by_id:
                return categorias_by_id[cid]
        except Exception:
            pass

    if "categoria" in row and row["categoria"] not in (None, ""):
        nombre = str(row["categoria"]).strip()
        if nombre:
            if nombre in categorias_by_name:
                return categorias_by_name[nombre]

            created = categoria_repo.get_or_create(nombre).obj
            categorias_by_id[getattr(created, "id", None)] = created
            categorias_by_name[nombre] = created
            return created

    return None

def _resolver_marca(row, marcas_by_id, marcas_by_name, marca_repo):
    if "marca_id" in row and row["marca_id"] not in (None, "", float("nan")):
        try:
            mid = int(row["marca_id"])
            if mid in marcas_by_id:
                return marcas_by_id[mid]
        except Exception:
            pass

    if "marca" in row and row["marca"] not in (None, ""):
        nombre = str(row["marca"]).strip()
        if nombre:
            if nombre in marcas_by_name:
                return marcas_by_name[nombre]

            created = marca_repo.get_or_create(nombre).obj
            marcas_by_id[getattr(created, "id", None)] = created
            marcas_by_name[nombre] = created
            return created

    return None

def _fetch_categorias_y_marca(df):
    cat_ids = set()
    if "categoria_id" in df.columns:
        for v in df["categoria_id"]:
            try:
                if v not in (None, "", float("nan")):
                    cat_ids.add(int(v))
            except Exception:
                pass
    cat_names = set()
    if "categoria" in df.columns:
        cat_names = {str(x).strip() for x in df["categoria"].dropna() if str(x).strip()}

    mar_ids = set()
    if "marca_id" in df.columns:
        for v in df["marca_id"]:
            try:
                if v not in (None, "", float("nan")):
                    mar_ids.add(int(v))
            except Exception:
                pass
    mar_names = set()
    if "marca" in df.columns:
        mar_names = {str(x).strip() for x in df["marca"].dropna() if str(x).strip()}


    categorias = list(Categoria.objects.filter(Q(id__in=cat_ids) | Q(nombre__in=cat_names)).only("id", "nombre"))
    marcas = list(Marca.objects.filter(Q(id__in=mar_ids) | Q(nombre__in=mar_names)).only("id", "nombre"))

    categorias_by_id = {c.id: c for c in categorias}
    categorias_by_name = {c.nombre: c for c in categorias}
    marcas_by_id = {m.id: m for m in marcas}
    marcas_by_name = {m.nombre: m for m in marcas}

    return categorias_by_id, categorias_by_name, marcas_by_id, marcas_by_name


@transaction.atomic
def importar_catalogo(*, file, fields_map: dict | None = None,
                      default_estado: str = "ACTIVO",
                      mode: str = "upsert"):
    """
    Importa catálogo de repuestos.
    Requeridos por fila: numero_pieza, descripcion
    Opcionales: estado, categoria_id|categoria_nombre, marca_id|marca_nombre
    mode:
      - upsert: crea si no existe, actualiza si existe
      - create-only: crea; si existe, lo cuenta como ignorado
      - update-only: actualiza solo si existe; si no, lo cuenta como ignorado
    """
    df = read_df(file)
    df = norm_cols_catalogo(df, fields_map or {})

    df["numero_pieza"] = df["numero_pieza"].astype(str).str.strip()
    df["descripcion"] = df["descripcion"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["numero_pieza"])

    if "estado" not in df.columns:
        df["estado"] = default_estado
    df["estado"] = df["estado"].apply(lambda v: _norm_estado(v, default_estado))


    # Buscar todos los numeros de repuestos afuera del for
    numeros = df["numero_pieza"].tolist()

    existentes_qs = Repuesto.objects.filter(numero_pieza__in=numeros).only(
        "id", "numero_pieza", "descripcion", "estado", "categoria_id", "marca_id"
    )
    existentes = {r.numero_pieza: r for r in existentes_qs}

    creados = actualizados = ignorados = 0
    errores = []

    categorias_by_id, categorias_by_name, marcas_by_id, marcas_by_name = _fetch_categorias_y_marca(df)

    for idx, row in df.iterrows():
        try:
            numero = row["numero_pieza"]
            descripcion = row["descripcion"]

            if not numero or not descripcion:
                raise ValueError("Las columnas 'numero_pieza' y 'descripcion' son obligatorias y no pueden estar vacías.")

            # Resolver opcionales
            categoria = _resolver_categoria(row, categorias_by_id, categorias_by_name, categoria_repo)
            marca = _resolver_marca(row, marcas_by_id, marcas_by_name, marca_repo)

            rep = existentes.get(numero)
            existe = rep is not None

            # Buscar existente
            rep = existentes.get(numero)
            existe = rep is not None

            if existe and mode == "create-only":
                ignorados += 1
                continue
            if not existe and mode == "update-only":
                ignorados += 1
                continue

            if existe:
                # actualizar
                changed = False
                if getattr(rep, "descripcion", "") != descripcion:
                    rep.description = descripcion; changed = True
                if getattr(rep, "estado", "") != row.get("estado"):
                    rep.status = row.get("estado"); changed = True
                if categoria is not None and getattr(rep, "categoria_id", None) != getattr(categoria, "id", None):
                    rep.categoria = categoria; changed = True
                if marca is not None and getattr(rep, "marca_id", None) != getattr(marca, "id", None):
                    rep.marca = marca; changed = True

                if changed:
                    rep.save()
                    actualizados += 1
                else:
                    ignorados += 1  # no hubo cambios
            else:
                # crear
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
            errores.append({"fila": int(idx) + 2, "motivo": str(ex)})

    return {
        "creados": creados,
        "actualizados": actualizados,
        "ignorados": ignorados,
        "rechazados": len(errores),
        "errores": errores,
        "mode": mode,
        "default_estado": default_estado,
    }
