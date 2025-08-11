# inventario/services/import_stock.py
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from ._helpers_movimientos import read_df            # <--- leer archivo desde aquí
from ._helpers_stock import norm_cols_stock          # <--- helper de stock

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

@transaction.atomic
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
    Genera SIEMPRE el movimiento correspondiente (AJUSTE+/AJUSTE-).
    mode = "set" -> setea el stock exacto; "sum" -> suma/resta la cantidad.
    """
    # 1) Leer archivo
    df = read_df(file)

    # 2) Mapeo estándar->archivo (permite override desde fields_map)
    default_map = {
        "numero_pieza": "repuesto",
        "cantidad": "cantidad",
        "deposito": "deposito",
    }
    if fields_map:
        default_map.update(fields_map)

    # 3) Normalizar/validar columnas de STOCK
    df = norm_cols_stock(df, default_map)

    required = {"numero_pieza", "cantidad", "deposito"}
    if not required.issubset(df.columns):
        faltan = sorted(required - set(df.columns))
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltan)}")

    # 4) Contexto
    taller = taller_repo.get(taller_id)
    procesados, errores = 0, []
    batch_id = uuid4().hex[:12]
    hoy = timezone.now().date()

    # 5) Filas
    for idx, row in df.iterrows():
        try:
            numero = str(row["numero_pieza"]).strip()
            dep_name = str(row["deposito"]).strip()
            raw_cant = row["cantidad"]

            if not numero or not dep_name:
                raise ValueError("Campos 'repuesto' y 'deposito' no pueden estar vacíos.")

            try:
                cant = int(raw_cant)
            except Exception:
                raise ValueError(f"Cantidad inválida: {raw_cant!r}")

            # Entidades
            repuesto = repuesto_repo.get_by_numero(numero)  # usa get_or_create si querés crear faltantes
            deposito = deposito_repo.get_or_create(taller, dep_name).obj
            rt = rt_repo.get_or_create(repuesto, taller).obj
            spd = stock_repo.get_or_create(rt, deposito).obj

            # Delta + tipo de movimiento
            if mode == "set":
                actual = int(getattr(spd, "qty_on_hand", 0))
                delta = cant - actual
            else:  # "sum"
                delta = cant

            if delta == 0:
                procesados += 1
                continue

            tipo = "AJUSTE+" if delta > 0 else "AJUSTE-"
            cantidad_mov = abs(delta)

            # Id externo por fila (idempotencia)
            externo_id = f"IMPSTK:{batch_id}:{idx+2}:{numero}:{dep_name}"

            # 1) Registrar movimiento (auditoría)
            mov_repo.crear_unico(
                spd,
                tipo=tipo,
                cantidad=cantidad_mov,
                fecha=hoy,
                externo_id=externo_id,
                documento=documento,
            )

            # 2) Aplicar al stock (si NO usás triggers que ya lo hagan)
            if tipo == "AJUSTE+":
                stock_repo.agregar(spd, cantidad_mov)
            else:
                stock_repo.egresar(spd, cantidad_mov, permitir_negativo=permitir_stock_negativo)

            procesados += 1

        except (NotFoundError, ValueError) as ex:
            errores.append({"fila": int(idx) + 2, "motivo": str(ex)})

    return {
        "procesados": procesados,
        "rechazados": len(errores),
        "errores": errores,
        "mode": mode,
        "batch": batch_id,
    }
