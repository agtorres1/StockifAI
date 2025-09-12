from collections import defaultdict
from django.db import transaction, connection
from django.db.models import F, Value, Case, When, IntegerField

from catalogo.models import RepuestoTaller
from ._helpers_movimientos import read_df, norm_cols, parse_fecha, norm_tipo
from ..models import StockPorDeposito, Movimiento
from ..repositories.taller_repo import TallerRepo
from ..repositories.deposito_repo import DepositoRepo
from ..repositories.repuesto_repo import RepuestoRepo
from ..repositories.repuesto_taller_repo import RepuestoTallerRepo
from ..repositories.stock_repo import StockRepo
from ..repositories.movimiento_repo import MovimientoRepo
from ..repositories.base import DuplicateError, NotFoundError, StockInsufficientError

taller_repo = TallerRepo()
deposito_repo = DepositoRepo()
repuesto_repo = RepuestoRepo()
rt_repo = RepuestoTallerRepo()
stock_repo = StockRepo()
mov_repo = MovimientoRepo()

BULK_BATCH = 2000
CHUNK_SIZE = 1000


def importar_movimientos(*, file, taller_id: int, fields_map: dict | None = None,
                         deposito_id: int | None = None, deposito_nombre: str | None = None,
                         permitir_stock_negativo: bool = True):
    """
    Versión optimizada del import de movimientos - asume repuestos y depósitos ya existen.
    """
    # 1) Leer y normalizar archivo
    df = read_df(file)
    df = norm_cols(df, fields_map or {})

    # 2) Configurar contexto
    taller = taller_repo.get(taller_id)
    deposito_default = None

    if deposito_id is not None:
        from inventario.models import Deposito
        deposito_default = Deposito.objects.get(pk=deposito_id, taller=taller)
    elif deposito_nombre:
        deposito_default = deposito_repo.get_or_create(taller, deposito_nombre).obj

    # 3) Configurar DB para bulk operations
    _configure_db_for_bulk_aws()

    try:
        # 4) Pre-procesar datos
        processed_data = _preprocess_data(df, deposito_default)

        # 5) Prefetch solo lo necesario (2-3 queries MAX)
        entities = _prefetch_entities_simple(processed_data, taller)

        # 6) Crear solo RT y SPD faltantes (mínimo)
        _create_minimal_entities(processed_data, entities, taller)

        # 7) Procesar movimientos en bulk
        result = _process_bulk_movimientos(
            processed_data, entities, permitir_stock_negativo
        )

        return result

    finally:
        _restore_db_config()


def _configure_db_for_bulk_aws():
    """Configura la DB para bulk operations."""
    try:
        with connection.cursor() as cursor:
            if connection.vendor == 'mysql':
                cursor.execute("SET SESSION net_write_timeout = 300")
                cursor.execute("SET SESSION autocommit = 0")
                cursor.execute("SET SESSION unique_checks = 0")

            elif connection.vendor == 'postgresql':
                cursor.execute("SET statement_timeout = '5min'")
                cursor.execute("SET synchronous_commit = OFF")
    except Exception:
        pass


def _restore_db_config():
    """Restaura configuración original."""
    try:
        with connection.cursor() as cursor:
            if connection.vendor == 'mysql':
                cursor.execute("SET SESSION autocommit = 1")
                cursor.execute("SET SESSION unique_checks = 1")

            elif connection.vendor == 'postgresql':
                cursor.execute("SET synchronous_commit = ON")
    except Exception:
        pass


def _preprocess_data(df, deposito_default):
    """Pre-procesa y valida los datos del archivo."""
    processed_rows = []
    errores = []

    for idx, row in df.iterrows():
        try:
            # Extraer y validar datos básicos
            pn = str(row['numero_pieza']).strip()
            fecha = parse_fecha(row['fecha'])
            tipo = norm_tipo(row['tipo'])
            cantidad = int(row['cantidad'])

            externo_id = None
            if 'externo_id' in row and row['externo_id'] not in (None, ''):
                externo_id = str(row['externo_id']).strip()

            # Determinar depósito
            dep_name = None
            if 'deposito' in row and row['deposito'] not in (None, ''):
                dep_name = str(row['deposito']).strip()
            elif deposito_default:
                dep_name = deposito_default.nombre
            else:
                raise ValueError("Depósito no especificado")

            documento = None
            if 'documento' in row and row['documento'] not in (None, ''):
                documento = str(row['documento']).strip()

            processed_rows.append({
                'idx': idx,
                'numero_pieza': pn,
                'fecha': fecha,
                'tipo': tipo,
                'cantidad': cantidad,
                'externo_id': externo_id,
                'deposito': dep_name,
                'documento': documento
            })

        except (ValueError, KeyError) as ex:
            errores.append({"fila": int(idx) + 2, "motivo": str(ex)})

    return {
        'rows': processed_rows,
        'errores': errores
    }


def _prefetch_entities_simple(processed_data, taller):
    """Prefetch simple - asume repuestos/depósitos existen. Solo 3 queries."""
    rows = processed_data['rows']

    # Extraer únicos
    numeros_pieza = list(set(row['numero_pieza'] for row in rows))
    depositos_nombres = list(set(row['deposito'] for row in rows))
    externos_ids = [row['externo_id'] for row in rows if row['externo_id']]

    # QUERY 1: Repuestos (deben existir)
    repuestos_list = repuesto_repo.list_by_numeros(numeros_pieza)
    repuestos_exist = {r.numero_pieza: r for r in repuestos_list}

    # Verificar que todos los repuestos existen
    faltantes = set(numeros_pieza) - set(repuestos_exist.keys())
    if faltantes:
        raise NotFoundError(f"Repuestos no encontrados: {', '.join(list(faltantes)[:5])}")

    # QUERY 2: Depósitos (deben existir)
    depositos_list = deposito_repo.list_by_nombres(taller, depositos_nombres)
    depositos_exist = {d.nombre: d for d in depositos_list}

    # Verificar que todos los depósitos existen
    deps_faltantes = set(depositos_nombres) - set(depositos_exist.keys())
    if deps_faltantes:
        raise NotFoundError(f"Depósitos no encontrados: {', '.join(list(deps_faltantes))}")

    # QUERY 3: RepuestoTaller existentes
    rt_list = rt_repo.list_by_taller_and_repuestos(taller, [r.pk for r in repuestos_exist.values()])
    rt_exist = {rt.repuesto_id: rt for rt in rt_list}

    # QUERY 4: Stock existente
    spd_exist = {}
    if rt_exist:
        spd_list = stock_repo.list_by_rt_ids_and_depositos(
            rt_ids=[rt.pk for rt in rt_exist.values()],
            deposito_ids=[d.pk for d in depositos_exist.values()]
        )
        spd_exist = {(s.repuesto_taller_id, s.deposito_id): s for s in spd_list}

    # QUERY 5: Movimientos existentes (para duplicados)
    movimientos_existentes = set()
    if externos_ids:
        from ..models import Movimiento
        existing_movs = Movimiento.objects.filter(externo_id__in=externos_ids).values_list('externo_id', flat=True)
        movimientos_existentes = set(existing_movs)

    return {
        'repuestos': repuestos_exist,
        'depositos': depositos_exist,
        'repuesto_taller': rt_exist,
        'stock': spd_exist,
        'movimientos_existentes': movimientos_existentes
    }


def _create_minimal_entities(processed_data, entities, taller):
    """Crea solo RT y SPD faltantes (mínimo necesario)."""
    rows = processed_data['rows']

    # 1) Crear RepuestoTaller faltantes
    rt_a_crear = []
    for numero_pieza, repuesto in entities['repuestos'].items():
        if repuesto.pk not in entities['repuesto_taller']:
            rt_a_crear.append({
                'repuesto_id': repuesto.pk,
                'taller_id': taller.id,
                'precio': 0,
                'costo': 0
            })

    if rt_a_crear:
        with transaction.atomic():
            created_rt = RepuestoTaller.objects.bulk_create(
                [RepuestoTaller(**data) for data in rt_a_crear],
                batch_size=CHUNK_SIZE
            )
            for i, rt in enumerate(created_rt):
                entities['repuesto_taller'][rt_a_crear[i]['repuesto_id']] = rt

    # 2) Crear StockPorDeposito faltantes
    spd_a_crear = []
    spd_keys_seen = set()

    for row in rows:
        numero = row['numero_pieza']
        dep_name = row['deposito']

        rep = entities['repuestos'][numero]
        dep = entities['depositos'][dep_name]
        rt = entities['repuesto_taller'][rep.pk]

        spd_key = (rt.pk, dep.pk)
        if spd_key not in entities['stock'] and spd_key not in spd_keys_seen:
            spd_a_crear.append({
                'repuesto_taller_id': rt.pk,
                'deposito_id': dep.pk,
                'cantidad': 0,
                'cantidad_minima': 0
            })
            spd_keys_seen.add(spd_key)

    if spd_a_crear:
        with transaction.atomic():
            created_spd = StockPorDeposito.objects.bulk_create(
                [StockPorDeposito(**data) for data in spd_a_crear],
                batch_size=CHUNK_SIZE
            )
            for i, spd in enumerate(created_spd):
                rt_id = spd_a_crear[i]['repuesto_taller_id']
                dep_id = spd_a_crear[i]['deposito_id']
                entities['stock'][(rt_id, dep_id)] = spd


def _process_bulk_movimientos(processed_data, entities, permitir_stock_negativo):
    """Procesa movimientos en bulk y actualiza stock."""

    rows = processed_data['rows']
    errores_iniciales = processed_data['errores']

    insertados = 0
    ignorados = 0
    errores = errores_iniciales.copy()

    movimientos_bulk = []
    deltas_por_spd = defaultdict(int)

    # Procesar cada fila
    for row in rows:
        try:
            # Verificar duplicado por externo_id
            if row['externo_id'] and row['externo_id'] in entities['movimientos_existentes']:
                ignorados += 1
                continue

            # Resolver entidades (deben existir)
            rep = entities['repuestos'][row['numero_pieza']]
            dep = entities['depositos'][row['deposito']]
            rt = entities['repuesto_taller'][rep.pk]
            spd = entities['stock'][(rt.pk, dep.pk)]

            # Calcular delta de stock
            if row['tipo'] in ("EGRESO", "AJUSTE-"):
                delta = -row['cantidad']
                # Validar stock negativo
                if not permitir_stock_negativo:
                    stock_actual = getattr(spd, 'cantidad', 0)
                    stock_futuro = stock_actual + deltas_por_spd[spd.pk] + delta
                    if stock_futuro < 0:
                        raise StockInsufficientError(
                            f"Stock insuficiente para {row['numero_pieza']} en {row['deposito']}. "
                            f"Actual: {stock_actual}, Requerido: {row['cantidad']}"
                        )
            else:  # INGRESO, AJUSTE+
                delta = row['cantidad']

            # Preparar movimiento
            movimientos_bulk.append(Movimiento(
                stock_por_deposito=spd,
                tipo=row['tipo'],
                cantidad=row['cantidad'],
                fecha=row['fecha'],
                externo_id=row['externo_id'],
                documento=row['documento']
            ))

            # Acumular delta para stock
            deltas_por_spd[spd.pk] += delta
            insertados += 1

        except (NotFoundError, StockInsufficientError, ValueError, KeyError) as ex:
            errores.append({"fila": row['idx'] + 2, "motivo": str(ex)})

    # Bulk create movimientos
    if movimientos_bulk:
        for i in range(0, len(movimientos_bulk), CHUNK_SIZE):
            chunk = movimientos_bulk[i:i + CHUNK_SIZE]
            with transaction.atomic():
                try:
                    Movimiento.objects.bulk_create(
                        chunk,
                        batch_size=CHUNK_SIZE,
                        ignore_conflicts=False
                    )
                except Exception:
                    # Manejar duplicados individualmente
                    for mov in chunk:
                        try:
                            mov.save()
                        except Exception:
                            ignorados += 1
                            insertados -= 1

    # Bulk update stock
    if deltas_por_spd:
        items = list(deltas_por_spd.items())
        for i in range(0, len(items), CHUNK_SIZE):
            chunk = items[i:i + CHUNK_SIZE]
            pks = [pk for pk, _ in chunk]
            whens = [When(pk=pk, then=F('cantidad') + Value(delta)) for pk, delta in chunk]

            with transaction.atomic():
                StockPorDeposito.objects.filter(pk__in=pks).update(
                    cantidad=Case(*whens, default=F('cantidad'), output_field=IntegerField())
                )

    return {
        "insertados": insertados,
        "ignorados": ignorados,
        "rechazados": len(errores),
        "errores": errores
    }