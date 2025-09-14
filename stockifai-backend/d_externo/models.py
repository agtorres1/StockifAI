from django.db import models
from user.models import Taller

class Inflacion(models.Model):
    fecha = models.DateField()
    ipc = models.DecimalField(max_digits=9, decimal_places=4)

    def __str__(self):
        return f"{self.fecha} - {self.ipc}"

class Patentamiento(models.Model):
    fecha = models.DateField()
    cantidad = models.FloatField()

    def __str__(self):
        return f"{self.fecha} - {self.cantidad}"


class IPSA(models.Model):
    fecha = models.DateField()
    ipsa = models.DecimalField(
        max_digits=10,
        decimal_places=6
    )

    def __str__(self):
        return f"{self.fecha} - {self.ipsa}"


class Prenda(models.Model):
    fecha = models.DateField()
    prenda = models.IntegerField()

    def __str__(self):
        return f"{self.fecha} - {self.prenda}"

class TasaInteresPrestamo(models.Model):
    fecha = models.DateField()
    tasa_interes = models.DecimalField(
        max_digits=10,
        decimal_places=6
    )

    def __str__(self):
        return f"{self.fecha} - {self.tasa_interes}"

class TipoCambio(models.Model):
    fecha = models.DateField()  # ejemplo: 2023-09-01
    tipo_cambio = models.DecimalField(
        max_digits=10,   # total de dígitos permitidos
        decimal_places=2 # dos decimales típicos para moneda
    )

    def __str__(self):
        return f"{self.fecha} - {self.tipo_cambio}"


class RegistroEntrenamiento_intermitente(models.Model):

    taller = models.ForeignKey(
        "user.Taller",
        on_delete=models.CASCADE,
        related_name="registros_intermitente",
        null=True,
        blank=True
        )
    """
    Representa las entradas de datos para un modelo de pronóstico de demanda,
    incluyendo información de la pieza, fecha, cantidad, variables económicas
    y estadísticas de ventas históricas.
    """
    # Identificadores y Demanda
    numero_pieza = models.CharField(max_length=255, verbose_name="Número de Parte")
    fecha = models.DateField(verbose_name="Fecha")
    cantidad = models.FloatField(verbose_name="Cantidad", null=True, blank=True)
    segmento_demanda = models.CharField(max_length=50, verbose_name="Segmento de Demanda")

    # Variables Económicas (con rezagos y promedios)
    inflacion_lag_1 = models.FloatField(verbose_name="Inflación (Lag 1)", null=True, blank=True)
    inflacion_lag_2 = models.FloatField(verbose_name="Inflación (Lag 2)", null=True, blank=True)
    inflacion_lag_3 = models.FloatField(verbose_name="Inflación (Lag 3)", null=True, blank=True)
    inflacion_lag_6 = models.FloatField(verbose_name="Inflación (Lag 6)", null=True, blank=True)
    inflacion_ema_3 = models.FloatField(verbose_name="Inflación (EMA 3)", null=True, blank=True)
    inflacion_ema_6 = models.FloatField(verbose_name="Inflación (EMA 6)", null=True, blank=True)
    inflacion_ema_12 = models.FloatField(verbose_name="Inflación (EMA 12)", null=True, blank=True)
    inflacion_delta = models.FloatField(verbose_name="Inflación (Delta)", null=True, blank=True)

    ipsa_lag_1 = models.FloatField(verbose_name="IPSA (Lag 1)", null=True, blank=True)
    ipsa_lag_2 = models.FloatField(verbose_name="IPSA (Lag 2)", null=True, blank=True)
    ipsa_lag_3 = models.FloatField(verbose_name="IPSA (Lag 3)", null=True, blank=True)
    ipsa_lag_6 = models.FloatField(verbose_name="IPSA (Lag 6)", null=True, blank=True)
    ipsa_ema_3 = models.FloatField(verbose_name="IPSA (EMA 3)", null=True, blank=True)
    ipsa_ema_6 = models.FloatField(verbose_name="IPSA (EMA 6)", null=True, blank=True)
    ipsa_ema_12 = models.FloatField(verbose_name="IPSA (EMA 12)", null=True, blank=True)
    ipsa_delta = models.FloatField(verbose_name="IPSA (Delta)", null=True, blank=True)

    # Comportamientos de Mercado
    patentamientos_lag_12 = models.FloatField(verbose_name="Patentamientos (Lag 12)", null=True, blank=True)
    patentamientos_lag_24 = models.FloatField(verbose_name="Patentamientos (Lag 24)", null=True, blank=True)
    patentamientos_lag_36 = models.FloatField(verbose_name="Patentamientos (Lag 36)", null=True, blank=True)
    patentamientos_ema_12 = models.FloatField(verbose_name="Patentamientos (EMA 12)", null=True, blank=True)
    patentamientos_ema_24 = models.FloatField(verbose_name="Patentamientos (EMA 24)", null=True, blank=True)
    patentamientos_delta = models.FloatField(verbose_name="Patentamientos (Delta)", null=True, blank=True)

    prenda_lag_1 = models.FloatField(verbose_name="Prendas (Lag 1)", null=True, blank=True)
    prenda_lag_2 = models.FloatField(verbose_name="Prendas (Lag 2)", null=True, blank=True)
    prenda_lag_3 = models.FloatField(verbose_name="Prendas (Lag 3)", null=True, blank=True)
    prenda_lag_6 = models.FloatField(verbose_name="Prendas (Lag 6)", null=True, blank=True)
    prenda_ema_3 = models.FloatField(verbose_name="Prendas (EMA 3)", null=True, blank=True)
    prenda_ema_6 = models.FloatField(verbose_name="Prendas (EMA 6)", null=True, blank=True)
    prenda_ema_12 = models.FloatField(verbose_name="Prendas (EMA 12)", null=True, blank=True)
    prenda_delta = models.FloatField(verbose_name="Prendas (Delta)", null=True, blank=True)

    tasa_de_interes_lag_1 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 1)", null=True, blank=True)
    tasa_de_interes_lag_2 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 2)", null=True, blank=True)
    tasa_de_interes_lag_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 3)", null=True, blank=True)
    tasa_de_interes_lag_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 6)", null=True, blank=True)
    tasa_de_interes_ema_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 3)", null=True, blank=True)
    tasa_de_interes_ema_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 6)", null=True, blank=True)
    tasa_de_interes_ema_12 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 12)", null=True, blank=True)
    tasa_de_interes_delta = models.FloatField(verbose_name="Tasa de Interés Préstamos (Delta)", null=True, blank=True)

    tipo_de_cambio_lag_1 = models.FloatField(verbose_name="Tipo de Cambio (Lag 1)", null=True, blank=True)
    tipo_de_cambio_lag_2 = models.FloatField(verbose_name="Tipo de Cambio (Lag 2)", null=True, blank=True)
    tipo_de_cambio_lag_3 = models.FloatField(verbose_name="Tipo de Cambio (Lag 3)", null=True, blank=True)
    tipo_de_cambio_lag_6 = models.FloatField(verbose_name="Tipo de Cambio (Lag 6)", null=True, blank=True)
    tipo_de_cambio_ema_3 = models.FloatField(verbose_name="Tipo de Cambio (EMA 3)", null=True, blank=True)
    tipo_de_cambio_ema_6 = models.FloatField(verbose_name="Tipo de Cambio (EMA 6)", null=True, blank=True)
    tipo_de_cambio_ema_12 = models.FloatField(verbose_name="Tipo de Cambio (EMA 12)", null=True, blank=True)
    tipo_de_cambio_delta = models.FloatField(verbose_name="Tipo de Cambio (Delta)", null=True, blank=True)

    # Variables de Tiempo (One-Hot Encoded)
    mes_1 = models.FloatField(default=0, null=True, blank=True)
    mes_2 = models.FloatField(default=0, null=True, blank=True)
    mes_3 = models.FloatField(default=0, null=True, blank=True)
    mes_4 = models.FloatField(default=0, null=True, blank=True)
    mes_5 = models.FloatField(default=0, null=True, blank=True)
    mes_6 = models.FloatField(default=0, null=True, blank=True)
    mes_7 = models.FloatField(default=0, null=True, blank=True)
    mes_8 = models.FloatField(default=0, null=True, blank=True)
    mes_9 = models.FloatField(default=0, null=True, blank=True)
    mes_10 = models.FloatField(default=0, null=True, blank=True)
    mes_11 = models.FloatField(default=0, null=True, blank=True)
    mes_12 = models.FloatField(default=0, null=True, blank=True)

    semana_1 = models.FloatField(default=0, null=True, blank=True)
    semana_2 = models.FloatField(default=0, null=True, blank=True)
    semana_3 = models.FloatField(default=0, null=True, blank=True)
    semana_4 = models.FloatField(default=0, null=True, blank=True)
    semana_5 = models.FloatField(default=0, null=True, blank=True)
    semana_6 = models.FloatField(default=0, null=True, blank=True)
    semana_7 = models.FloatField(default=0, null=True, blank=True)
    semana_8 = models.FloatField(default=0, null=True, blank=True)
    semana_9 = models.FloatField(default=0, null=True, blank=True)
    semana_10 = models.FloatField(default=0, null=True, blank=True)
    semana_11 = models.FloatField(default=0, null=True, blank=True)
    semana_12 = models.FloatField(default=0, null=True, blank=True)
    semana_13 = models.FloatField(default=0, null=True, blank=True)
    semana_14 = models.FloatField(default=0, null=True, blank=True)
    semana_15 = models.FloatField(default=0, null=True, blank=True)
    semana_16 = models.FloatField(default=0, null=True, blank=True)
    semana_17 = models.FloatField(default=0, null=True, blank=True)
    semana_18 = models.FloatField(default=0, null=True, blank=True)
    semana_19 = models.FloatField(default=0, null=True, blank=True)
    semana_20 = models.FloatField(default=0, null=True, blank=True)
    semana_21 = models.FloatField(default=0, null=True, blank=True)
    semana_22 = models.FloatField(default=0, null=True, blank=True)
    semana_23 = models.FloatField(default=0, null=True, blank=True)
    semana_24 = models.FloatField(default=0, null=True, blank=True)
    semana_25 = models.FloatField(default=0, null=True, blank=True)
    semana_26 = models.FloatField(default=0, null=True, blank=True)
    semana_27 = models.FloatField(default=0, null=True, blank=True)
    semana_28 = models.FloatField(default=0, null=True, blank=True)
    semana_29 = models.FloatField(default=0, null=True, blank=True)
    semana_30 = models.FloatField(default=0, null=True, blank=True)
    semana_31 = models.FloatField(default=0, null=True, blank=True)
    semana_32 = models.FloatField(default=0, null=True, blank=True)
    semana_33 = models.FloatField(default=0, null=True, blank=True)
    semana_34 = models.FloatField(default=0, null=True, blank=True)
    semana_35 = models.FloatField(default=0, null=True, blank=True)
    semana_36 = models.FloatField(default=0, null=True, blank=True)
    semana_37 = models.FloatField(default=0, null=True, blank=True)
    semana_38 = models.FloatField(default=0, null=True, blank=True)
    semana_39 = models.FloatField(default=0, null=True, blank=True)
    semana_40 = models.FloatField(default=0, null=True, blank=True)
    semana_41 = models.FloatField(default=0, null=True, blank=True)
    semana_42 = models.FloatField(default=0, null=True, blank=True)
    semana_43 = models.FloatField(default=0, null=True, blank=True)
    semana_44 = models.FloatField(default=0, null=True, blank=True)
    semana_45 = models.FloatField(default=0, null=True, blank=True)
    semana_46 = models.FloatField(default=0, null=True, blank=True)
    semana_47 = models.FloatField(default=0, null=True, blank=True)
    semana_48 = models.FloatField(default=0, null=True, blank=True)
    semana_49 = models.FloatField(default=0, null=True, blank=True)
    semana_50 = models.FloatField(default=0, null=True, blank=True)
    semana_51 = models.FloatField(default=0, null=True, blank=True)
    semana_52 = models.FloatField(default=0, null=True, blank=True)

    trimestre_1 = models.FloatField(default=0, null=True, blank=True)
    trimestre_2 = models.FloatField(default=0, null=True, blank=True)
    trimestre_3 = models.FloatField(default=0, null=True, blank=True)
    trimestre_4 = models.FloatField(default=0, null=True, blank=True)

    # Eventos y Características Adicionales
    es_semana_feriado = models.BooleanField(verbose_name="Es Semana Feriada", null=True, blank=True)
    hubo_venta = models.BooleanField(verbose_name="Hubo Venta", null=True, blank=True)
    dias_hasta_feriado = models.IntegerField(verbose_name="Días Hasta Feriado", null=True, blank=True)

    # Historial de Ventas (Lagged)
    ventas_t_1 = models.FloatField(verbose_name="Ventas (t-1)", null=True, blank=True)
    ventas_t_2 = models.FloatField(verbose_name="Ventas (t-2)", null=True, blank=True)
    ventas_t_3 = models.FloatField(verbose_name="Ventas (t-3)", null=True, blank=True)
    ventas_t_4 = models.FloatField(verbose_name="Ventas (t-4)", null=True, blank=True)
    ventas_t_5 = models.FloatField(verbose_name="Ventas (t-5)", null=True, blank=True)
    ventas_t_6 = models.FloatField(verbose_name="Ventas (t-6)", null=True, blank=True)
    ventas_t_7 = models.FloatField(verbose_name="Ventas (t-7)", null=True, blank=True)
    ventas_t_8 = models.FloatField(verbose_name="Ventas (t-8)", null=True, blank=True)
    ventas_t_9 = models.FloatField(verbose_name="Ventas (t-9)", null=True, blank=True)
    ventas_t_10 = models.FloatField(verbose_name="Ventas (t-10)", null=True, blank=True)
    ventas_t_11 = models.FloatField(verbose_name="Ventas (t-11)", null=True, blank=True)
    ventas_t_12 = models.FloatField(verbose_name="Ventas (t-12)", null=True, blank=True)
    ventas_t_13 = models.FloatField(verbose_name="Ventas (t-13)", null=True, blank=True)
    ventas_t_14 = models.FloatField(verbose_name="Ventas (t-14)", null=True, blank=True)
    ventas_t_15 = models.FloatField(verbose_name="Ventas (t-15)", null=True, blank=True)
    ventas_t_16 = models.FloatField(verbose_name="Ventas (t-16)", null=True, blank=True)
    ventas_t_17 = models.FloatField(verbose_name="Ventas (t-17)", null=True, blank=True)
    ventas_t_18 = models.FloatField(verbose_name="Ventas (t-18)", null=True, blank=True)
    ventas_t_19 = models.FloatField(verbose_name="Ventas (t-19)", null=True, blank=True)
    ventas_t_20 = models.FloatField(verbose_name="Ventas (t-20)", null=True, blank=True)
    ventas_t_21 = models.FloatField(verbose_name="Ventas (t-21)", null=True, blank=True)
    ventas_t_22 = models.FloatField(verbose_name="Ventas (t-22)", null=True, blank=True)
    ventas_t_23 = models.FloatField(verbose_name="Ventas (t-23)", null=True, blank=True)
    ventas_t_24 = models.FloatField(verbose_name="Ventas (t-24)", null=True, blank=True)
    ventas_t_25 = models.FloatField(verbose_name="Ventas (t-25)", null=True, blank=True)
    ventas_t_26 = models.FloatField(verbose_name="Ventas (t-26)", null=True, blank=True)

    # Estadísticas de Ventas
    media_ultimas_4 = models.FloatField(verbose_name="Media Últimas 4 Semanas", null=True, blank=True)
    std_pasada_4_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 4 Semanas", null=True, blank=True)
    coef_var_4 = models.FloatField(verbose_name="Coeficiente de Variación 4 Semanas", null=True, blank=True)

    media_ultimas_8 = models.FloatField(verbose_name="Media Últimas 8 Semanas", null=True, blank=True)
    std_pasada_8_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 8 Semanas", null=True, blank=True)
    coef_var_8 = models.FloatField(verbose_name="Coeficiente de Variación 8 Semanas", null=True, blank=True)

    media_ultimas_12 = models.FloatField(verbose_name="Media Últimas 12 Semanas", null=True, blank=True)
    std_pasada_12_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 12 Semanas", null=True, blank=True)
    coef_var_12 = models.FloatField(verbose_name="Coeficiente de Variación 12 Semanas", null=True, blank=True)

    media_ultimas_26 = models.FloatField(verbose_name="Media Últimas 26 Semanas", null=True, blank=True)
    std_pasada_26_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 26 Semanas", null=True, blank=True)
    coef_var_26 = models.FloatField(verbose_name="Coeficiente de Variación 26 Semanas", null=True, blank=True)

    def __str__(self):
        return f"{self.numero_pieza} - {self.fecha}"



class RegistroEntrenamiento_Frecuencia_Alta(models.Model):

    """
    Modelo de Django para la tabla de registros de entrenamiento de frecuencia alta.
    """

    taller = models.ForeignKey(
        "user.Taller",
        on_delete=models.CASCADE,
        related_name="registros_frecuencia_alta",
        null=True,
        blank=True
    )

    # Identificadores y Demanda (Estos no deben ser nulos)
    numero_pieza = models.CharField(max_length=255, verbose_name="Número de Parte")
    fecha = models.DateField(verbose_name="Fecha")
    cantidad = models.FloatField(verbose_name="Cantidad", null=True, blank=True)
    segmento_demanda = models.CharField(max_length=50, verbose_name="Segmento de Demanda")

    # Variables Económicas (con rezagos y promedios)
    inflacion_lag_1 = models.FloatField(verbose_name="Inflación (Lag 1)", null=True, blank=True)
    inflacion_lag_2 = models.FloatField(verbose_name="Inflación (Lag 2)", null=True, blank=True)
    inflacion_lag_3 = models.FloatField(verbose_name="Inflación (Lag 3)", null=True, blank=True)
    inflacion_lag_6 = models.FloatField(verbose_name="Inflación (Lag 6)", null=True, blank=True)
    inflacion_ema_3 = models.FloatField(verbose_name="Inflación (EMA 3)", null=True, blank=True)
    inflacion_ema_6 = models.FloatField(verbose_name="Inflación (EMA 6)", null=True, blank=True)
    inflacion_ema_12 = models.FloatField(verbose_name="Inflación (EMA 12)", null=True, blank=True)
    inflacion_delta = models.FloatField(verbose_name="Inflación (Delta)", null=True, blank=True)

    ipsa_lag_1 = models.FloatField(verbose_name="IPSA (Lag 1)", null=True, blank=True)
    ipsa_lag_2 = models.FloatField(verbose_name="IPSA (Lag 2)", null=True, blank=True)
    ipsa_lag_3 = models.FloatField(verbose_name="IPSA (Lag 3)", null=True, blank=True)
    ipsa_lag_6 = models.FloatField(verbose_name="IPSA (Lag 6)", null=True, blank=True)
    ipsa_ema_3 = models.FloatField(verbose_name="IPSA (EMA 3)", null=True, blank=True)
    ipsa_ema_6 = models.FloatField(verbose_name="IPSA (EMA 6)", null=True, blank=True)
    ipsa_ema_12 = models.FloatField(verbose_name="IPSA (EMA 12)", null=True, blank=True)
    ipsa_delta = models.FloatField(verbose_name="IPSA (Delta)", null=True, blank=True)

    # Comportamientos de Mercado
    patentamientos_lag_12 = models.FloatField(verbose_name="Patentamientos (Lag 12)", null=True, blank=True)
    patentamientos_lag_24 = models.FloatField(verbose_name="Patentamientos (Lag 24)", null=True, blank=True)
    patentamientos_lag_36 = models.FloatField(verbose_name="Patentamientos (Lag 36)", null=True, blank=True)
    patentamientos_ema_12 = models.FloatField(verbose_name="Patentamientos (EMA 12)", null=True, blank=True)
    patentamientos_ema_24 = models.FloatField(verbose_name="Patentamientos (EMA 24)", null=True, blank=True)
    patentamientos_delta = models.FloatField(verbose_name="Patentamientos (Delta)", null=True, blank=True)

    prenda_lag_1 = models.FloatField(verbose_name="Prendas (Lag 1)", null=True, blank=True)
    prenda_lag_2 = models.FloatField(verbose_name="Prendas (Lag 2)", null=True, blank=True)
    prenda_lag_3 = models.FloatField(verbose_name="Prendas (Lag 3)", null=True, blank=True)
    prenda_lag_6 = models.FloatField(verbose_name="Prendas (Lag 6)", null=True, blank=True)
    prenda_ema_3 = models.FloatField(verbose_name="Prendas (EMA 3)", null=True, blank=True)
    prenda_ema_6 = models.FloatField(verbose_name="Prendas (EMA 6)", null=True, blank=True)
    prenda_ema_12 = models.FloatField(verbose_name="Prendas (EMA 12)", null=True, blank=True)
    prenda_delta = models.FloatField(verbose_name="Prendas (Delta)", null=True, blank=True)

    tasa_de_interes_lag_1 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 1)", null=True, blank=True)
    tasa_de_interes_lag_2 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 2)", null=True, blank=True)
    tasa_de_interes_lag_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 3)", null=True, blank=True)
    tasa_de_interes_lag_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 6)", null=True, blank=True)
    tasa_de_interes_ema_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 3)", null=True, blank=True)
    tasa_de_interes_ema_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 6)", null=True, blank=True)
    tasa_de_interes_ema_12 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 12)", null=True, blank=True)
    tasa_de_interes_delta = models.FloatField(verbose_name="Tasa de Interés Préstamos (Delta)", null=True, blank=True)

    tipo_de_cambio_lag_1 = models.FloatField(verbose_name="Tipo de Cambio (Lag 1)", null=True, blank=True)
    tipo_de_cambio_lag_2 = models.FloatField(verbose_name="Tipo de Cambio (Lag 2)", null=True, blank=True)
    tipo_de_cambio_lag_3 = models.FloatField(verbose_name="Tipo de Cambio (Lag 3)", null=True, blank=True)
    tipo_de_cambio_lag_6 = models.FloatField(verbose_name="Tipo de Cambio (Lag 6)", null=True, blank=True)
    tipo_de_cambio_ema_3 = models.FloatField(verbose_name="Tipo de Cambio (EMA 3)", null=True, blank=True)
    tipo_de_cambio_ema_6 = models.FloatField(verbose_name="Tipo de Cambio (EMA 6)", null=True, blank=True)
    tipo_de_cambio_ema_12 = models.FloatField(verbose_name="Tipo de Cambio (EMA 12)", null=True, blank=True)
    tipo_de_cambio_delta = models.FloatField(verbose_name="Tipo de Cambio (Delta)", null=True, blank=True)

    # Variables de Tiempo (One-Hot Encoded)
    mes_1 = models.FloatField(default=0, null=True, blank=True)
    mes_2 = models.FloatField(default=0, null=True, blank=True)
    mes_3 = models.FloatField(default=0, null=True, blank=True)
    mes_4 = models.FloatField(default=0, null=True, blank=True)
    mes_5 = models.FloatField(default=0, null=True, blank=True)
    mes_6 = models.FloatField(default=0, null=True, blank=True)
    mes_7 = models.FloatField(default=0, null=True, blank=True)
    mes_8 = models.FloatField(default=0, null=True, blank=True)
    mes_9 = models.FloatField(default=0, null=True, blank=True)
    mes_10 = models.FloatField(default=0, null=True, blank=True)
    mes_11 = models.FloatField(default=0, null=True, blank=True)
    mes_12 = models.FloatField(default=0, null=True, blank=True)

    semana_1 = models.FloatField(default=0, null=True, blank=True)
    semana_2 = models.FloatField(default=0, null=True, blank=True)
    semana_3 = models.FloatField(default=0, null=True, blank=True)
    semana_4 = models.FloatField(default=0, null=True, blank=True)
    semana_5 = models.FloatField(default=0, null=True, blank=True)
    semana_6 = models.FloatField(default=0, null=True, blank=True)
    semana_7 = models.FloatField(default=0, null=True, blank=True)
    semana_8 = models.FloatField(default=0, null=True, blank=True)
    semana_9 = models.FloatField(default=0, null=True, blank=True)
    semana_10 = models.FloatField(default=0, null=True, blank=True)
    semana_11 = models.FloatField(default=0, null=True, blank=True)
    semana_12 = models.FloatField(default=0, null=True, blank=True)
    semana_13 = models.FloatField(default=0, null=True, blank=True)
    semana_14 = models.FloatField(default=0, null=True, blank=True)
    semana_15 = models.FloatField(default=0, null=True, blank=True)
    semana_16 = models.FloatField(default=0, null=True, blank=True)
    semana_17 = models.FloatField(default=0, null=True, blank=True)
    semana_18 = models.FloatField(default=0, null=True, blank=True)
    semana_19 = models.FloatField(default=0, null=True, blank=True)
    semana_20 = models.FloatField(default=0, null=True, blank=True)
    semana_21 = models.FloatField(default=0, null=True, blank=True)
    semana_22 = models.FloatField(default=0, null=True, blank=True)
    semana_23 = models.FloatField(default=0, null=True, blank=True)
    semana_24 = models.FloatField(default=0, null=True, blank=True)
    semana_25 = models.FloatField(default=0, null=True, blank=True)
    semana_26 = models.FloatField(default=0, null=True, blank=True)
    semana_27 = models.FloatField(default=0, null=True, blank=True)
    semana_28 = models.FloatField(default=0, null=True, blank=True)
    semana_29 = models.FloatField(default=0, null=True, blank=True)
    semana_30 = models.FloatField(default=0, null=True, blank=True)
    semana_31 = models.FloatField(default=0, null=True, blank=True)
    semana_32 = models.FloatField(default=0, null=True, blank=True)
    semana_33 = models.FloatField(default=0, null=True, blank=True)
    semana_34 = models.FloatField(default=0, null=True, blank=True)
    semana_35 = models.FloatField(default=0, null=True, blank=True)
    semana_36 = models.FloatField(default=0, null=True, blank=True)
    semana_37 = models.FloatField(default=0, null=True, blank=True)
    semana_38 = models.FloatField(default=0, null=True, blank=True)
    semana_39 = models.FloatField(default=0, null=True, blank=True)
    semana_40 = models.FloatField(default=0, null=True, blank=True)
    semana_41 = models.FloatField(default=0, null=True, blank=True)
    semana_42 = models.FloatField(default=0, null=True, blank=True)
    semana_43 = models.FloatField(default=0, null=True, blank=True)
    semana_44 = models.FloatField(default=0, null=True, blank=True)
    semana_45 = models.FloatField(default=0, null=True, blank=True)
    semana_46 = models.FloatField(default=0, null=True, blank=True)
    semana_47 = models.FloatField(default=0, null=True, blank=True)
    semana_48 = models.FloatField(default=0, null=True, blank=True)
    semana_49 = models.FloatField(default=0, null=True, blank=True)
    semana_50 = models.FloatField(default=0, null=True, blank=True)
    semana_51 = models.FloatField(default=0, null=True, blank=True)
    semana_52 = models.FloatField(default=0, null=True, blank=True)

    trimestre_1 = models.FloatField(default=0, null=True, blank=True)
    trimestre_2 = models.FloatField(default=0, null=True, blank=True)
    trimestre_3 = models.FloatField(default=0, null=True, blank=True)
    trimestre_4 = models.FloatField(default=0, null=True, blank=True)

    # Eventos y Características Adicionales
    es_semana_feriado = models.BooleanField(verbose_name="Es Semana Feriada", null=True, blank=True)
    hubo_venta = models.BooleanField(verbose_name="Hubo Venta", null=True, blank=True)
    dias_hasta_feriado = models.IntegerField(verbose_name="Días Hasta Feriado", null=True, blank=True)

    # Historial de Ventas (Lagged)
    ventas_t_1 = models.FloatField(verbose_name="Ventas (t-1)", null=True, blank=True)
    ventas_t_2 = models.FloatField(verbose_name="Ventas (t-2)", null=True, blank=True)
    ventas_t_3 = models.FloatField(verbose_name="Ventas (t-3)", null=True, blank=True)
    ventas_t_4 = models.FloatField(verbose_name="Ventas (t-4)", null=True, blank=True)
    ventas_t_5 = models.FloatField(verbose_name="Ventas (t-5)", null=True, blank=True)
    ventas_t_6 = models.FloatField(verbose_name="Ventas (t-6)", null=True, blank=True)
    ventas_t_7 = models.FloatField(verbose_name="Ventas (t-7)", null=True, blank=True)
    ventas_t_8 = models.FloatField(verbose_name="Ventas (t-8)", null=True, blank=True)
    ventas_t_9 = models.FloatField(verbose_name="Ventas (t-9)", null=True, blank=True)
    ventas_t_10 = models.FloatField(verbose_name="Ventas (t-10)", null=True, blank=True)
    ventas_t_11 = models.FloatField(verbose_name="Ventas (t-11)", null=True, blank=True)
    ventas_t_12 = models.FloatField(verbose_name="Ventas (t-12)", null=True, blank=True)
    ventas_t_13 = models.FloatField(verbose_name="Ventas (t-13)", null=True, blank=True)
    ventas_t_14 = models.FloatField(verbose_name="Ventas (t-14)", null=True, blank=True)
    ventas_t_15 = models.FloatField(verbose_name="Ventas (t-15)", null=True, blank=True)
    ventas_t_16 = models.FloatField(verbose_name="Ventas (t-16)", null=True, blank=True)
    ventas_t_17 = models.FloatField(verbose_name="Ventas (t-17)", null=True, blank=True)
    ventas_t_18 = models.FloatField(verbose_name="Ventas (t-18)", null=True, blank=True)
    ventas_t_19 = models.FloatField(verbose_name="Ventas (t-19)", null=True, blank=True)
    ventas_t_20 = models.FloatField(verbose_name="Ventas (t-20)", null=True, blank=True)
    ventas_t_21 = models.FloatField(verbose_name="Ventas (t-21)", null=True, blank=True)
    ventas_t_22 = models.FloatField(verbose_name="Ventas (t-22)", null=True, blank=True)
    ventas_t_23 = models.FloatField(verbose_name="Ventas (t-23)", null=True, blank=True)
    ventas_t_24 = models.FloatField(verbose_name="Ventas (t-24)", null=True, blank=True)
    ventas_t_25 = models.FloatField(verbose_name="Ventas (t-25)", null=True, blank=True)
    ventas_t_26 = models.FloatField(verbose_name="Ventas (t-26)", null=True, blank=True)
    ventas_t_27 = models.FloatField(verbose_name="Ventas (t-27)", null=True, blank=True)
    ventas_t_28 = models.FloatField(verbose_name="Ventas (t-28)", null=True, blank=True)
    ventas_t_29 = models.FloatField(verbose_name="Ventas (t-29)", null=True, blank=True)
    ventas_t_30 = models.FloatField(verbose_name="Ventas (t-30)", null=True, blank=True)
    ventas_t_31 = models.FloatField(verbose_name="Ventas (t-31)", null=True, blank=True)
    ventas_t_32 = models.FloatField(verbose_name="Ventas (t-32)", null=True, blank=True)
    ventas_t_33 = models.FloatField(verbose_name="Ventas (t-33)", null=True, blank=True)
    ventas_t_34 = models.FloatField(verbose_name="Ventas (t-34)", null=True, blank=True)
    ventas_t_35 = models.FloatField(verbose_name="Ventas (t-35)", null=True, blank=True)
    ventas_t_36 = models.FloatField(verbose_name="Ventas (t-36)", null=True, blank=True)
    ventas_t_37 = models.FloatField(verbose_name="Ventas (t-37)", null=True, blank=True)
    ventas_t_38 = models.FloatField(verbose_name="Ventas (t-38)", null=True, blank=True)
    ventas_t_39 = models.FloatField(verbose_name="Ventas (t-39)", null=True, blank=True)
    ventas_t_40 = models.FloatField(verbose_name="Ventas (t-40)", null=True, blank=True)
    ventas_t_41 = models.FloatField(verbose_name="Ventas (t-41)", null=True, blank=True)
    ventas_t_42 = models.FloatField(verbose_name="Ventas (t-42)", null=True, blank=True)
    ventas_t_43 = models.FloatField(verbose_name="Ventas (t-43)", null=True, blank=True)
    ventas_t_44 = models.FloatField(verbose_name="Ventas (t-44)", null=True, blank=True)
    ventas_t_45 = models.FloatField(verbose_name="Ventas (t-45)", null=True, blank=True)
    ventas_t_46 = models.FloatField(verbose_name="Ventas (t-46)", null=True, blank=True)
    ventas_t_47 = models.FloatField(verbose_name="Ventas (t-47)", null=True, blank=True)
    ventas_t_48 = models.FloatField(verbose_name="Ventas (t-48)", null=True, blank=True)
    ventas_t_49 = models.FloatField(verbose_name="Ventas (t-49)", null=True, blank=True)
    ventas_t_50 = models.FloatField(verbose_name="Ventas (t-50)", null=True, blank=True)
    ventas_t_51 = models.FloatField(verbose_name="Ventas (t-51)", null=True, blank=True)
    ventas_t_52 = models.FloatField(verbose_name="Ventas (t-52)", null=True, blank=True)


    # Estadísticas de Ventas
    media_ultimas_4 = models.FloatField(verbose_name="Media Últimas 4 Semanas", null=True, blank=True)
    std_pasada_4_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 4 Semanas", null=True, blank=True)
    coef_var_4 = models.FloatField(verbose_name="Coeficiente de Variación 4 Semanas", null=True, blank=True)

    media_ultimas_8 = models.FloatField(verbose_name="Media Últimas 8 Semanas", null=True, blank=True)
    std_pasada_8_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 8 Semanas", null=True, blank=True)
    coef_var_8 = models.FloatField(verbose_name="Coeficiente de Variación 8 Semanas", null=True, blank=True)

    media_ultimas_12 = models.FloatField(verbose_name="Media Últimas 12 Semanas", null=True, blank=True)
    std_pasada_12_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 12 Semanas", null=True, blank=True)
    coef_var_12 = models.FloatField(verbose_name="Coeficiente de Variación 12 Semanas", null=True, blank=True)

    media_ultimas_26 = models.FloatField(verbose_name="Media Últimas 26 Semanas", null=True, blank=True)
    std_pasada_26_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 26 Semanas", null=True, blank=True)
    coef_var_26 = models.FloatField(verbose_name="Coeficiente de Variación 26 Semanas", null=True, blank=True)

    media_ultimas_52 = models.FloatField(verbose_name="Media Últimas 52 Semanas", null=True, blank=True)
    std_pasada_52_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 52 Semanas", null=True, blank=True)
    coef_var_52 = models.FloatField(verbose_name="Coeficiente de Variación 52 Semanas", null=True, blank=True)

    def __str__(self):
        return f"{self.numero_pieza} - {self.fecha}"