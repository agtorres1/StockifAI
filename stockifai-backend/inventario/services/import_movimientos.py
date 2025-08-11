from django.db import transaction
from ._helpers_movimientos import read_df, norm_cols, parse_fecha, norm_tipo  # <--- singular

from ..repositories.taller_repo import TallerRepo
from ..repositories.deposito_repo import DepositoRepo
from ..repositories.repuesto_repo import RepuestoRepo
from ..repositories.repuesto_taller_repo import RepuestoTallerRepo
from ..repositories.stock_repo import StockRepo
from ..repositories.movimiento_repo import MovimientoRepo
from ..repositories.base import DuplicateError, NotFoundError, StockInsufficientError

taller_repo = TallerRepo(); deposito_repo = DepositoRepo(); repuesto_repo = RepuestoRepo()
rt_repo = RepuestoTallerRepo(); stock_repo = StockRepo(); mov_repo = MovimientoRepo()

@transaction.atomic
def importar_movimientos(*, file, taller_id: int, fields_map: dict | None = None,
                         deposito_id: int | None = None, deposito_nombre: str | None = None,
                         permitir_stock_negativo: bool = True):
    df = read_df(file); df = norm_cols(df, fields_map or {})
    taller = taller_repo.get(taller_id)
    deposito_default = None
    if deposito_id is not None:
        from inventario.models import Deposito
        deposito_default = Deposito.objects.get(pk=deposito_id, taller=taller)
    elif deposito_nombre:
        deposito_default = deposito_repo.get_or_create(taller, deposito_nombre).obj
    insertados = ignorados = 0; errores = []
    for idx, row in df.iterrows():
        try:
            pn = str(row['numero_pieza']).strip(); fecha = parse_fecha(row['fecha'])
            tipo = norm_tipo(row['tipo']); cantidad = int(row['cantidad'])
            externo_id = (str(row['externo_id']).strip() if 'externo_id' in row and row['externo_id'] not in (None, '') else None)
            dep_name = (str(row['deposito']).strip() if 'deposito' in row and row['deposito'] not in (None, '') else None)
            documento = (str(row['documento']).strip() if 'documento' in row and row['documento'] not in (None, '') else None)
            if dep_name: deposito = deposito_repo.get_or_create(taller, dep_name).obj
            elif deposito_default: deposito = deposito_default
            else: raise ValueError("Depósito no especificado (fila sin 'deposito' y sin default).")
            repuesto = repuesto_repo.get_by_numero(pn)
            rt = rt_repo.get_or_create(repuesto, taller).obj
            spd = stock_repo.get_or_create(rt, deposito).obj
            mov = mov_repo.crear_unico(spd, tipo=tipo, cantidad=cantidad, fecha=fecha, externo_id=externo_id, documento=documento)
            if tipo in ("INGRESO","AJUSTE+"): stock_repo.agregar(spd, cantidad)
            elif tipo in ("EGRESO","AJUSTE-"): stock_repo.egresar(spd, cantidad, permitir_negativo=permitir_stock_negativo)
            insertados += 1
        except DuplicateError: ignorados += 1
        except (NotFoundError, StockInsufficientError, ValueError) as ex:
            errores.append({"fila": int(idx) + 2, "motivo": str(ex)})
    return {"insertados": insertados, "ignorados": ignorados, "rechazados": len(errores), "errores": errores}
