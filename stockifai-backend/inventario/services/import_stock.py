# inventario/services/import_stock.py
from collections import defaultdict
from uuid import uuid4

from django.db import transaction, connection, ProgrammingError
from django.db.models import F, Value, Case, When, IntegerField
from django.utils import timezone

from catalogo.models import Repuesto, RepuestoTaller
from ._helpers_movimientos import read_df
from ._helpers_stock import norm_cols_stock
from ..models import Movimiento, Deposito, StockPorDeposito

from ..repositories.base import NotFoundError
from ..repositories.deposito_repo import DepositoRepo
from ..repositories.movimiento_repo import MovimientoRepo
from ..repositories.repuesto_repo import RepuestoRepo
from ..repositories.repuesto_taller_repo import RepuestoTallerRepo
from ..repositories.stock_repo import StockRepo
from ..repositories.taller_repo import TallerRepo

taller_repo = TallerRepo()
deposito_repo = DepositoRepo()
repuesto_repo = RepuestoRepo()
rt_repo = RepuestoTallerRepo()
stock_repo = StockRepo()
mov_repo = MovimientoRepo()

BULK_BATCH = 2000
CHUNK_SIZE = 2000

@transaction.atomic  # <- TODO EN UNA SOLA TRANSACCIÓN
def importar_stock(
        *, file, taller_id: int, fields_map: dict | None = None,
        mode: str = "set", permitir_stock_negativo: bool = False,
        documento: str = "IMPORTACIÓN DE STOCK"
):
    """
    Importa stock por (repuesto, deposito) desde un Excel/CSV con columnas:
    - repuesto (número de pieza)
    - cantidad (int)
    - deposito (nombre)
    Genera SIEMPRE el movimiento correspondiente (AJUSTE_INICIAL+/AJUSTE_INICIAL-).
    mode = "set" -> setea el stock exacto; "sum" -> suma/resta la cantidad.
    """
    # 1) Leer archivo
    df = read_df(file)

    # 2) Mapear columnas (permite override)
    default_map = {"numero_pieza": "repuesto", "cantidad": "cantidad", "deposito": "deposito"}
    if fields_map:
        default_map.update(fields_map)
    df = norm_cols_stock(df, default_map)

    # 3) Validar mínimas + normalizar
    required = {"numero_pieza", "cantidad", "deposito"}
    if not required.issubset(df.columns):
        faltan = sorted(required - set(df.columns))
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltan)}")

    df["numero_pieza"] = df["numero_pieza"].astype(str).str.strip()
    df["deposito"] = df["deposito"].astype(str).str.strip()
    df = df.dropna(subset=["numero_pieza", "deposito", "cantidad"])
    df = df[df["numero_pieza"] != ""]
    # Consolidar duplicados del archivo
    df = df.groupby(["numero_pieza", "deposito"], as_index=False)["cantidad"].sum()

    # 4) Contexto
    taller = taller_repo.get(taller_id)
    batch_id = uuid4().hex[:12]
    hoy = timezone.now().date()

    # Tunings no destructivos; evitamos tocar autocommit/unique_checks
    _configure_db_for_bulk_aws()

    # 5) Prefetch + creación masiva de faltantes (sin commits intermedios)
    entities = _prefetch_all_entities(df, taller)
    _create_missing_entities(df, entities, taller)

    # 6) Movimientos en bulk + UPDATE masivo
    result = _process_movements_and_deltas(
        df, entities, batch_id, hoy, documento, mode, permitir_stock_negativo
    )

    return result


def _configure_db_for_bulk_aws():
    """Tunings seguros por sesión"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION net_write_timeout = 300")
            cursor.execute("SET SESSION net_read_timeout = 300")
            cursor.execute("SET SESSION wait_timeout = 3600")
            cursor.execute("SET SESSION interactive_timeout = 3600")
    except Exception:
        pass

def _prefetch_all_entities(df, taller):
    numeros = df["numero_pieza"].unique().tolist()
    deps_nombres = df["deposito"].unique().tolist()

    repuestos_exist = {r.numero_pieza: r for r in repuesto_repo.list_by_numeros(numeros)}
    depositos_exist = {d.nombre: d for d in deposito_repo.list_by_nombres(taller, deps_nombres)}

    rt_exist = {}
    if repuestos_exist:
        rt_list = rt_repo.list_by_taller_and_repuestos(taller, [r.pk for r in repuestos_exist.values()])
        rt_exist = {rt.repuesto_id: rt for rt in rt_list}

    spd_exist = {}
    if rt_exist and depositos_exist:
        spd_list = stock_repo.list_by_rt_ids_and_depositos(
            rt_ids=[rt.pk for rt in rt_exist.values()],
            deposito_ids=[d.pk for d in depositos_exist.values()]
        )
        spd_exist = {(s.repuesto_taller_id, s.deposito_id): s for s in spd_list}

    return {
        'repuestos': repuestos_exist,
        'depositos': depositos_exist,
        'repuesto_taller': rt_exist,
        'stock': spd_exist,
    }


def _create_missing_entities(df, entities, taller):
    # Repuestos faltantes
    numeros_faltantes = [row["numero_pieza"] for _, row in df.iterrows()
                         if row["numero_pieza"] not in entities['repuestos']]
    if numeros_faltantes:
        nuevos = list({n for n in numeros_faltantes})
        created = Repuesto.objects.bulk_create(
            [Repuesto(numero_pieza=n, descripcion=n, estado='ACTIVO') for n in nuevos],
            batch_size=CHUNK_SIZE,
            ignore_conflicts=True,
        )
        # Refetch para asegurar PKs (ignore_conflicts no devuelve todo)
        for r in repuesto_repo.list_by_numeros(nuevos):
            entities['repuestos'][r.numero_pieza] = r

    # Depósitos faltantes
    deps_faltantes = [row["deposito"] for _, row in df.iterrows()
                      if row["deposito"] not in entities['depositos']]
    if deps_faltantes:
        nuevos = list({d for d in deps_faltantes})
        Deposito.objects.bulk_create(
            [Deposito(taller=taller, nombre=nm) for nm in nuevos],
            batch_size=CHUNK_SIZE,
            ignore_conflicts=True,
        )
        for d in deposito_repo.list_by_nombres(taller, nuevos):
            entities['depositos'][d.nombre] = d

    repuesto_ids = [r.pk for r in entities['repuestos'].values()]
    deposito_ids_by_name = {nm: d.pk for nm, d in entities['depositos'].items()}

    # RT faltantes
    faltan_rt_rep_ids = [rid for rid in repuesto_ids if rid not in entities['repuesto_taller']]
    if faltan_rt_rep_ids:
        RepuestoTaller.objects.bulk_create(
            [RepuestoTaller(taller=taller, repuesto_id=rid, precio=0, costo=0) for rid in faltan_rt_rep_ids],
            batch_size=CHUNK_SIZE,
            ignore_conflicts=True,
        )

    # Refetch
    rt_list = RepuestoTaller.objects.filter(
        taller=taller,
        repuesto_id__in=repuesto_ids
    ).only("id_repuesto_taller", "repuesto_id")  # <- PK correcto

    # Clave del dict = repuesto_id  (no el pk del RT)
    entities['repuesto_taller'] = {rt.repuesto_id: rt for rt in rt_list}

    # SPD faltantes
    pairs_needed = set()
    for _, row in df.iterrows():
        rep = entities['repuestos'][row["numero_pieza"]]
        dep = entities['depositos'][row["deposito"]]
        rt = entities['repuesto_taller'][rep.pk]
        pairs_needed.add((rt.pk, dep.pk))

    ya = set(entities['stock'].keys())
    crear = [p for p in pairs_needed if p not in ya]
    if crear:
        StockPorDeposito.objects.bulk_create(
            [StockPorDeposito(repuesto_taller_id=rt_id, deposito_id=dep_id, cantidad=0, cantidad_minima=0)
             for (rt_id, dep_id) in crear],
            batch_size=CHUNK_SIZE,
            ignore_conflicts=True,
        )
        # Refetch sólo los creados
        spd_new = StockPorDeposito.objects.filter(
            repuesto_taller_id__in=[rt for (rt, _) in crear],
            deposito_id__in=[dp for (_, dp) in crear]
        ).only("id", "repuesto_taller_id", "deposito_id", "cantidad")
        for s in spd_new:
            entities['stock'][(s.repuesto_taller_id, s.deposito_id)] = s


def _process_movements_and_deltas(df, entities, batch_id, hoy, documento, mode, permitir_stock_negativo):
    procesados = 0
    errores = []
    movimientos_bulk = []
    deltas_por_spd = defaultdict(int)

    for idx, row in df.iterrows():
        try:
            numero = row["numero_pieza"]
            dep_name = row["deposito"]
            cant = int(row["cantidad"])

            rep = entities['repuestos'][numero]
            dep = entities['depositos'][dep_name]
            rt = entities['repuesto_taller'][rep.pk]
            spd = entities['stock'][(rt.pk, dep.pk)]

            if mode == "set":
                actual = int(getattr(spd, "cantidad", 0))
                delta = cant - actual
            else:
                delta = cant

            if delta == 0:
                procesados += 1
                continue

            if not permitir_stock_negativo:
                actual = int(getattr(spd, "cantidad", 0))
                if actual + delta < 0:
                    errores.append({
                        "fila": int(idx) + 2,
                        "motivo": f"Stock insuficiente en depósito '{dep_name}' para repuesto '{numero}': {actual} + ({delta}) < 0"
                    })
                    continue

            tipo = "INICIAL+" if delta > 0 else "INICIAL-"
            cantidad_mov = abs(delta)
            externo_id = f"IMPSTK:{batch_id}:{idx + 2}:{numero}:{dep_name}"

            movimientos_bulk.append(Movimiento(
                stock_por_deposito=spd,
                tipo=tipo,
                cantidad=cantidad_mov,
                fecha=hoy,
                externo_id=externo_id,
                documento=documento,
            ))
            deltas_por_spd[spd.pk] += delta
            procesados += 1

        except (NotFoundError, ValueError, KeyError) as ex:
            errores.append({"Fila": int(idx) + 2, "Motivo": str(ex)})

    # bulk_create (todo dentro de la misma transacción)
    if movimientos_bulk:
        Movimiento.objects.bulk_create(
            movimientos_bulk,
            batch_size=BULK_BATCH,
        )

    # UPDATE masivo de stock
    if deltas_por_spd:
        items = list(deltas_por_spd.items())
        for i in range(0, len(items), CHUNK_SIZE):
            chunk = items[i:i + CHUNK_SIZE]
            pks = [pk for pk, _ in chunk]
            whens = [When(pk=pk, then=F('cantidad') + Value(d)) for pk, d in chunk]
            StockPorDeposito.objects.filter(pk__in=pks).update(
                cantidad=Case(*whens, default=F('cantidad'), output_field=IntegerField())
            )

    return {
        "procesados": procesados,
        "rechazados": len(errores),
        "errores": errores,
        "mode": mode,
        "batch": batch_id,
    }