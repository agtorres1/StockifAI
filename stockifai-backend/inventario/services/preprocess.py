from inventario.repositories.movimiento_repo import MovimientoRepo

def fetch_movimientos_egreso_5anios(taller_id: int):
    taller_id = 1 # para probar
    qs = MovimientoRepo().get_egresos_ultimos_5_anios(taller_id=taller_id)
    res = list(qs)

    return res
