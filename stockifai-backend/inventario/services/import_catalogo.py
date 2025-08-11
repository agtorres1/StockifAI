# inventario/services/import_catalogo.py
from django.db import transaction
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

def _resolver_categoria(row):
    if "categoria_id" in row and row["categoria_id"] not in (None, "", float("nan")):
        try:
            cid = int(row["categoria_id"])
            return categoria_repo.get(cid)
        except Exception:
            # id inválido -> intentar por nombre si hay
            pass
    if "categoria_nombre" in row and row["categoria_nombre"] not in (None, ""):
        nombre = str(row["categoria_nombre"]).strip()
        return categoria_repo.get_or_create(nombre).obj
    return None  # opcional

def _resolver_marca(row):
    if "marca_id" in row and row["marca_id"] not in (None, "", float("nan")):
        try:
            mid = int(row["marca_id"])
            return marca_repo.get(mid)
        except Exception:
            pass
    if "marca_nombre" in row and row["marca_nombre"] not in (None, ""):
        nombre = str(row["marca_nombre"]).strip()
        return marca_repo.get_or_create(nombre).obj
    return None  # opcional

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

    creados = actualizados = ignorados = 0
    errores = []

    for idx, row in df.iterrows():
        try:
            numero = str(row["numero_pieza"]).strip()
            descripcion = str(row["descripcion"]).strip()

            if not numero or not descripcion:
                raise ValueError("Las columnas 'numero_pieza' y 'descripcion' son obligatorias y no pueden estar vacías.")

            estado = _norm_estado(row.get("estado"), default_estado)

            # Resolver opcionales
            categoria = _resolver_categoria(row)
            marca = _resolver_marca(row)

            # Buscar existente
            try:
                rep = repuesto_repo.get_by_numero(numero)
                existe = True
            except NotFoundError:
                rep = None
                existe = False

            if existe and mode == "create-only":
                ignorados += 1
                continue
            if not existe and mode == "update-only":
                ignorados += 1
                continue

            if existe:
                # actualizar
                changed = False
                if getattr(rep, "description", "") != descripcion:
                    rep.description = descripcion; changed = True
                if getattr(rep, "status", "") != estado:
                    rep.status = estado; changed = True
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
                    estado=estado,
                    categoria=categoria,
                    marca=marca,
                )
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
