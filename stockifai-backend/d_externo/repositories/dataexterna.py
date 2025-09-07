from d_externo.models import Inflacion, Patentamiento, IPSA, Prenda, TasaInteresPrestamo, TipoCambio,  RegistroEntrenamiento_intermitente, RegistroEntrenamientoFrecuenciaAlta

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



def obtener_registroentrenamiento_intermitente():
    """
    Devuelve todos los registros de RegistroEntrenamiento_intermitente
    como una lista de diccionarios.
    """
    registros = RegistroEntrenamiento_intermitente.objects.all()
    lista_diccionarios = list(registros.values())
    return lista_diccionarios


def guardar_registroentrenamiento_intermitente(datos):
    """
    Guarda un registro en la base de datos.

    Parámetro:
        datos (dict): Diccionario con los campos y valores a guardar.
    """
    registro = RegistroEntrenamiento_intermitente.objects.create(**datos)
    return registro




def obtener_registros_frecuencia_alta():
    """
    Devuelve todos los registros de RegistroEntrenamientoFrecuenciaAlta
    como una lista de diccionarios.
    """
    registros = RegistroEntrenamientoFrecuenciaAlta.objects.all()
    lista_diccionarios = list(registros.values())
    return lista_diccionarios


def guardar_registro_frecuencia_alta(datos):
    """
    Guarda un registro en la base de datos para RegistroEntrenamientoFrecuenciaAlta.

    Parámetro:
        datos (dict): Diccionario con los campos y valores a guardar.
    """
    registro = RegistroEntrenamientoFrecuenciaAlta.objects.create(**datos)
    return registro
