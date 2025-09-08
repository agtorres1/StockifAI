from d_externo.models import Inflacion, Patentamiento, IPSA, Prenda, TasaInteresPrestamo, TipoCambio,  RegistroEntrenamiento_intermitente, RegistroEntrenamiento_Frecuencia_Alta
from user.models import Taller

def obtener_todas_las_inflaciones():
    """
    Retorna una lista de diccionarios con todos los registros de Inflacion.
    Cada diccionario tiene: {'fecha': ..., 'ipc': ...}
    """
    inflaciones = Inflacion.objects.all()
    resultado = []
    for infl in inflaciones:
        resultado.append({
            'fecha': infl.fecha,
            'ipc': float(infl.ipc)  # opcional convertir a float para facilidad
        })
    return resultado

def obtener_todos_los_patentamientos():
    return list(Patentamiento.objects.all().values('fecha', 'cantidad'))

def obtener_todos_los_ipsa():
    return list(IPSA.objects.all().values('fecha', 'ipsa'))

def obtener_todas_las_prendas():
    return list(Prenda.objects.all().values('fecha', 'prenda'))

def obtener_todas_las_tasas_interes():
    return list(TasaInteresPrestamo.objects.all().values('fecha', 'tasa_interes'))

def obtener_todos_los_tipos_cambio():
    return list(TipoCambio.objects.all().values('fecha', 'tipo_cambio'))


def obtener_registroentrenamiento_intermitente(taller_id: int):
    """
    Devuelve todos los registros de RegistroEntrenamiento_intermitente
    de un taller específico como una lista de diccionarios.
    """
    registros = RegistroEntrenamiento_intermitente.objects.filter(taller_id=taller_id)
    lista_diccionarios = list(registros.values())
    return lista_diccionarios


def guardar_registroentrenamiento_intermitente(datos: dict, taller: Taller):
    """
    Guarda un registro en la base de datos para RegistroEntrenamiento_intermitente.
    """
    try:
        registro = RegistroEntrenamiento_intermitente.objects.create(
            taller=taller,
            **datos
        )
        return registro
    except Taller.DoesNotExist:
        raise ValueError(f"No se encontró un Taller con id={taller_id}")


def obtener_registroentrenamiento_frecuencia_alta(taller_id: int):
    """
    Devuelve todos los registros de RegistroEntrenamientoFrecuenciaAlta
    de un taller específico como una lista de diccionarios.
    """
    registros = RegistroEntrenamiento_Frecuencia_Alta.objects.filter(taller_id=taller_id)
    lista_diccionarios = list(registros.values())
    return lista_diccionarios


def guardar_registroentrenamiento_frecuencia_alta(datos: dict, taller: Taller):
    """
    Guarda un registro en la base de datos para RegistroEntrenamientoFrecuenciaAlta.
    """
    try:
        registro = RegistroEntrenamiento_Frecuencia_Alta.objects.create(
            taller=taller,
            **datos
        )
        return registro
    except Taller.DoesNotExist:
        raise ValueError(f"No se encontró un Taller con id={taller_id}")