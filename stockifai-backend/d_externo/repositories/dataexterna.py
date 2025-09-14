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

def borrar_registroentrenamiento_intermitente(taller: Taller):
    """
    Borra todos los registros de la tabla RegistroEntrenamiento_intermitente
    asociados a un taller específico.
    """
    try:
        registros_borrados, _ = RegistroEntrenamiento_intermitente.objects.filter(taller=taller).delete()
        print(f"Se eliminaron {registros_borrados} registros de Intermitente del taller {taller.nombre}.")
    except Exception as e:
        print(f"Error al borrar registros de Intermitente: {e}")
        raise

def guardar_registroentrenamiento_intermitente(datos: dict, taller: Taller):
    """
    Guarda un registro en la base de datos para RegistroEntrenamiento_intermitente.
    """
    numero_pieza = datos.pop('numero_pieza')
    try:
        registro = RegistroEntrenamiento_intermitente.objects.update_or_create(
            numero_pieza=numero_pieza,
            defaults={
                **datos, # Todos los demás datos del diccionario
                'taller': taller,
                'segmento_demanda': 'intermitente'
            }
        )
        return registro
    except Exception as e:
        print(f"Error al crear registro de Intermitente: {e}")
        raise


def obtener_registroentrenamiento_frecuencia_alta(taller_id: int):
    """
    Devuelve todos los registros de RegistroEntrenamientoFrecuenciaAlta
    de un taller específico como una lista de diccionarios.
    """
    registros = RegistroEntrenamiento_Frecuencia_Alta.objects.filter(taller_id=taller_id)
    lista_diccionarios = list(registros.values())
    return lista_diccionarios

def borrar_registroentrenamiento_frecuencia_alta(taller: Taller):
    """
    Borra todos los registros de la tabla RegistroEntrenamiento_intermitente
    asociados a un taller específico.
    """
    try:
        registros_borrados, _ = RegistroEntrenamiento_Frecuencia_Alta.objects.filter(taller=taller).delete()
        print(f"Se eliminaron {registros_borrados} registros de Frecuencia Alta del taller {taller.nombre}.")
    except Exception as e:
        print(f"Error al borrar registros de Intermitente: {e}")
        raise
def guardar_registroentrenamiento_frecuencia_alta(datos: dict, taller: Taller):
    """
    Guarda un registro en la base de datos para RegistroEntrenamientoFrecuenciaAlta.
    """
    numero_pieza = datos.pop('numero_pieza')
    try:
        registro = RegistroEntrenamiento_Frecuencia_Alta.objects.update_or_create(
            numero_pieza=numero_pieza,
            defaults={
                **datos, # Todos los demás datos del diccionario
                'taller': taller,
                'segmento_demanda': 'frecuencia_alta'
            }
        )
        return registro
    except Exception as e:
        print(f"Error al crear registro de Frecuencia Alta: {e}")
        raise