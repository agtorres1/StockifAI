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
        null=True,  # temporal para no romper la migración
        blank=True
        )
    """
    Representa las entradas de datos para un modelo de pronóstico de demanda,
    incluyendo información de la pieza, fecha, cantidad, variables económicas
    y estadísticas de ventas históricas.
    """
    # Identificadores y Demanda
    numero_parte = models.CharField(max_length=255, verbose_name="Número de Parte")
    fecha = models.DateField(verbose_name="Fecha")
    cantidad = models.FloatField(verbose_name="Cantidad")
    segmento_demanda = models.CharField(max_length=50, verbose_name="Segmento de Demanda")

    # Variables Económicas (con rezagos y promedios)
    inflacion_lag_1 = models.FloatField(verbose_name="Inflación (Lag 1)")
    inflacion_lag_2 = models.FloatField(verbose_name="Inflación (Lag 2)")
    inflacion_lag_3 = models.FloatField(verbose_name="Inflación (Lag 3)")
    inflacion_lag_6 = models.FloatField(verbose_name="Inflación (Lag 6)")
    inflacion_ema_3 = models.FloatField(verbose_name="Inflación (EMA 3)")
    inflacion_ema_6 = models.FloatField(verbose_name="Inflación (EMA 6)")
    inflacion_ema_12 = models.FloatField(verbose_name="Inflación (EMA 12)")
    inflacion_delta = models.FloatField(verbose_name="Inflación (Delta)")

    ipsa_lag_1 = models.FloatField(verbose_name="IPSA (Lag 1)")
    ipsa_lag_2 = models.FloatField(verbose_name="IPSA (Lag 2)")
    ipsa_lag_3 = models.FloatField(verbose_name="IPSA (Lag 3)")
    ipsa_lag_6 = models.FloatField(verbose_name="IPSA (Lag 6)")
    ipsa_ema_3 = models.FloatField(verbose_name="IPSA (EMA 3)")
    ipsa_ema_6 = models.FloatField(verbose_name="IPSA (EMA 6)")
    ipsa_ema_12 = models.FloatField(verbose_name="IPSA (EMA 12)")
    ipsa_delta = models.FloatField(verbose_name="IPSA (Delta)")

    # Comportamientos de Mercado
    patentamientos_lag_12 = models.FloatField(verbose_name="Patentamientos (Lag 12)")
    patentamientos_lag_24 = models.FloatField(verbose_name="Patentamientos (Lag 24)")
    patentamientos_lag_36 = models.FloatField(verbose_name="Patentamientos (Lag 36)")
    patentamientos_ema_12 = models.FloatField(verbose_name="Patentamientos (EMA 12)")
    patentamientos_ema_24 = models.FloatField(verbose_name="Patentamientos (EMA 24)")
    patentamientos_delta = models.FloatField(verbose_name="Patentamientos (Delta)")

    prendas_lag_1 = models.FloatField(verbose_name="Prendas (Lag 1)")
    prendas_lag_2 = models.FloatField(verbose_name="Prendas (Lag 2)")
    prendas_lag_3 = models.FloatField(verbose_name="Prendas (Lag 3)")
    prendas_lag_6 = models.FloatField(verbose_name="Prendas (Lag 6)")
    prendas_ema_3 = models.FloatField(verbose_name="Prendas (EMA 3)")
    prendas_ema_6 = models.FloatField(verbose_name="Prendas (EMA 6)")
    prendas_ema_12 = models.FloatField(verbose_name="Prendas (EMA 12)")
    prendas_delta = models.FloatField(verbose_name="Prendas (Delta)")

    tasa_de_interes_lag_1 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 1)")
    tasa_de_interes_lag_2 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 2)")
    tasa_de_interes_lag_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 3)")
    tasa_de_interes_lag_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 6)")
    tasa_de_interes_ema_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 3)")
    tasa_de_interes_ema_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 6)")
    tasa_de_interes_ema_12 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 12)")
    tasa_de_interes_delta = models.FloatField(verbose_name="Tasa de Interés Préstamos (Delta)")

    tipo_de_cambio_lag_1 = models.FloatField(verbose_name="Tipo de Cambio (Lag 1)")
    tipo_de_cambio_lag_2 = models.FloatField(verbose_name="Tipo de Cambio (Lag 2)")
    tipo_de_cambio_lag_3 = models.FloatField(verbose_name="Tipo de Cambio (Lag 3)")
    tipo_de_cambio_lag_6 = models.FloatField(verbose_name="Tipo de Cambio (Lag 6)")
    tipo_de_cambio_ema_3 = models.FloatField(verbose_name="Tipo de Cambio (EMA 3)")
    tipo_de_cambio_ema_6 = models.FloatField(verbose_name="Tipo de Cambio (EMA 6)")
    tipo_de_cambio_ema_12 = models.FloatField(verbose_name="Tipo de Cambio (EMA 12)")
    tipo_de_cambio_delta = models.FloatField(verbose_name="Tipo de Cambio (Delta)")

    # Variables de Tiempo (One-Hot Encoded)
    mes_1 = models.FloatField(default=0)
    mes_2 = models.FloatField(default=0)
    mes_3 = models.FloatField(default=0)
    mes_4 = models.FloatField(default=0)
    mes_5 = models.FloatField(default=0)
    mes_6 = models.FloatField(default=0)
    mes_7 = models.FloatField(default=0)
    mes_8 = models.FloatField(default=0)
    mes_9 = models.FloatField(default=0)
    mes_10 = models.FloatField(default=0)
    mes_11 = models.FloatField(default=0)
    mes_12 = models.FloatField(default=0)

    semana_1 = models.FloatField(default=0)
    semana_2 = models.FloatField(default=0)
    semana_3 = models.FloatField(default=0)
    semana_4 = models.FloatField(default=0)
    semana_5 = models.FloatField(default=0)
    semana_6 = models.FloatField(default=0)
    semana_7 = models.FloatField(default=0)
    semana_8 = models.FloatField(default=0)
    semana_9 = models.FloatField(default=0)
    semana_10 = models.FloatField(default=0)
    semana_11 = models.FloatField(default=0)
    semana_12 = models.FloatField(default=0)
    semana_13 = models.FloatField(default=0)
    semana_14 = models.FloatField(default=0)
    semana_15 = models.FloatField(default=0)
    semana_16 = models.FloatField(default=0)
    semana_17 = models.FloatField(default=0)
    semana_18 = models.FloatField(default=0)
    semana_19 = models.FloatField(default=0)
    semana_20 = models.FloatField(default=0)
    semana_21 = models.FloatField(default=0)
    semana_22 = models.FloatField(default=0)
    semana_23 = models.FloatField(default=0)
    semana_24 = models.FloatField(default=0)
    semana_25 = models.FloatField(default=0)
    semana_26 = models.FloatField(default=0)
    semana_27 = models.FloatField(default=0)
    semana_28 = models.FloatField(default=0)
    semana_29 = models.FloatField(default=0)
    semana_30 = models.FloatField(default=0)
    semana_31 = models.FloatField(default=0)
    semana_32 = models.FloatField(default=0)
    semana_33 = models.FloatField(default=0)
    semana_34 = models.FloatField(default=0)
    semana_35 = models.FloatField(default=0)
    semana_36 = models.FloatField(default=0)
    semana_37 = models.FloatField(default=0)
    semana_38 = models.FloatField(default=0)
    semana_39 = models.FloatField(default=0)
    semana_40 = models.FloatField(default=0)
    semana_41 = models.FloatField(default=0)
    semana_42 = models.FloatField(default=0)
    semana_43 = models.FloatField(default=0)
    semana_44 = models.FloatField(default=0)
    semana_45 = models.FloatField(default=0)
    semana_46 = models.FloatField(default=0)
    semana_47 = models.FloatField(default=0)
    semana_48 = models.FloatField(default=0)
    semana_49 = models.FloatField(default=0)
    semana_50 = models.FloatField(default=0)
    semana_51 = models.FloatField(default=0)
    semana_52 = models.FloatField(default=0)

    trimestre_1 = models.FloatField(default=0)
    trimestre_2 = models.FloatField(default=0)
    trimestre_3 = models.FloatField(default=0)
    trimestre_4 = models.FloatField(default=0)

    # Eventos y Características Adicionales
    es_semana_feriado = models.BooleanField(verbose_name="Es Semana Feriada")
    hubo_venta = models.BooleanField(verbose_name="Hubo Venta")
    dias_hasta_feriado = models.IntegerField(verbose_name="Días Hasta Feriado")

    # Historial de Ventas (Lagged)
    ventas_t_1 = models.FloatField(verbose_name="Ventas (t-1)")
    ventas_t_2 = models.FloatField(verbose_name="Ventas (t-2)")
    ventas_t_3 = models.FloatField(verbose_name="Ventas (t-3)")
    ventas_t_4 = models.FloatField(verbose_name="Ventas (t-4)")
    ventas_t_5 = models.FloatField(verbose_name="Ventas (t-5)")
    ventas_t_6 = models.FloatField(verbose_name="Ventas (t-6)")
    ventas_t_7 = models.FloatField(verbose_name="Ventas (t-7)")
    ventas_t_8 = models.FloatField(verbose_name="Ventas (t-8)")
    ventas_t_9 = models.FloatField(verbose_name="Ventas (t-9)")
    ventas_t_10 = models.FloatField(verbose_name="Ventas (t-10)")
    ventas_t_11 = models.FloatField(verbose_name="Ventas (t-11)")
    ventas_t_12 = models.FloatField(verbose_name="Ventas (t-12)")
    ventas_t_13 = models.FloatField(verbose_name="Ventas (t-13)")
    ventas_t_14 = models.FloatField(verbose_name="Ventas (t-14)")
    ventas_t_15 = models.FloatField(verbose_name="Ventas (t-15)")
    ventas_t_16 = models.FloatField(verbose_name="Ventas (t-16)")
    ventas_t_17 = models.FloatField(verbose_name="Ventas (t-17)")
    ventas_t_18 = models.FloatField(verbose_name="Ventas (t-18)")
    ventas_t_19 = models.FloatField(verbose_name="Ventas (t-19)")
    ventas_t_20 = models.FloatField(verbose_name="Ventas (t-20)")
    ventas_t_21 = models.FloatField(verbose_name="Ventas (t-21)")
    ventas_t_22 = models.FloatField(verbose_name="Ventas (t-22)")
    ventas_t_23 = models.FloatField(verbose_name="Ventas (t-23)")
    ventas_t_24 = models.FloatField(verbose_name="Ventas (t-24)")
    ventas_t_25 = models.FloatField(verbose_name="Ventas (t-25)")
    ventas_t_26 = models.FloatField(verbose_name="Ventas (t-26)")
    ventas_t_27 = models.FloatField(verbose_name="Ventas (t-27)")
    ventas_t_28 = models.FloatField(verbose_name="Ventas (t-28)")

    # Estadísticas de Ventas
    media_ultimas_4 = models.FloatField(verbose_name="Media Últimas 4 Semanas")
    std_pasada_4_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 4 Semanas")
    coef_var_4 = models.FloatField(verbose_name="Coeficiente de Variación 4 Semanas")

    media_ultimas_8 = models.FloatField(verbose_name="Media Últimas 8 Semanas")
    std_pasada_8_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 8 Semanas")
    coef_var_8 = models.FloatField(verbose_name="Coeficiente de Variación 8 Semanas")

    media_ultimas_12 = models.FloatField(verbose_name="Media Últimas 12 Semanas")
    std_pasada_12_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 12 Semanas")
    coef_var_12 = models.FloatField(verbose_name="Coeficiente de Variación 12 Semanas")

    media_ultimas_26 = models.FloatField(verbose_name="Media Últimas 26 Semanas")
    std_pasada_26_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 26 Semanas")
    coef_var_26 = models.FloatField(verbose_name="Coeficiente de Variación 26 Semanas")

    media_ultimas_52 = models.FloatField(verbose_name="Media Últimas 52 Semanas")
    std_pasada_52_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 52 Semanas")
    coef_var_52 = models.FloatField(verbose_name="Coeficiente de Variación 52 Semanas")

    def __str__(self):
        return f"{self.numero_parte} - {self.fecha}"



class RegistroEntrenamiento_Frecuencia_Alta(models.Model):

    """
    Modelo de Django para la tabla de registros de entrenamiento de frecuencia alta.

    Diseñado para piezas con comportamiento de demanda frecuente, incluyendo
    variables económicas y estadísticas detalladas.
    """

    taller = models.ForeignKey(
        Taller,  # referencia directa al modelo importado
        on_delete=models.CASCADE,
        related_name="registros_frecuencia_alta",
        null=True,  # temporalmente
        blank=True
    )

    # Identificadores y Demanda
    numero_parte = models.CharField(max_length=255, verbose_name="Número de Parte")
    fecha = models.DateField(verbose_name="Fecha")
    cantidad = models.FloatField(verbose_name="Cantidad")
    segmento_demanda = models.CharField(max_length=50, verbose_name="Segmento de Demanda")

    # Variables Económicas (con rezagos y promedios)
    inflacion_lag_1 = models.FloatField(verbose_name="Inflación (Lag 1)")
    inflacion_lag_2 = models.FloatField(verbose_name="Inflación (Lag 2)")
    inflacion_lag_3 = models.FloatField(verbose_name="Inflación (Lag 3)")
    inflacion_lag_6 = models.FloatField(verbose_name="Inflación (Lag 6)")
    inflacion_ema_3 = models.FloatField(verbose_name="Inflación (EMA 3)")
    inflacion_ema_6 = models.FloatField(verbose_name="Inflación (EMA 6)")
    inflacion_ema_12 = models.FloatField(verbose_name="Inflación (EMA 12)")
    inflacion_delta = models.FloatField(verbose_name="Inflación (Delta)")

    ipsa_lag_1 = models.FloatField(verbose_name="IPSA (Lag 1)")
    ipsa_lag_2 = models.FloatField(verbose_name="IPSA (Lag 2)")
    ipsa_lag_3 = models.FloatField(verbose_name="IPSA (Lag 3)")
    ipsa_lag_6 = models.FloatField(verbose_name="IPSA (Lag 6)")
    ipsa_ema_3 = models.FloatField(verbose_name="IPSA (EMA 3)")
    ipsa_ema_6 = models.FloatField(verbose_name="IPSA (EMA 6)")
    ipsa_ema_12 = models.FloatField(verbose_name="IPSA (EMA 12)")
    ipsa_delta = models.FloatField(verbose_name="IPSA (Delta)")

    # Comportamientos de Mercado
    patentamientos_lag_12 = models.FloatField(verbose_name="Patentamientos (Lag 12)")
    patentamientos_lag_24 = models.FloatField(verbose_name="Patentamientos (Lag 24)")
    patentamientos_lag_36 = models.FloatField(verbose_name="Patentamientos (Lag 36)")
    patentamientos_ema_12 = models.FloatField(verbose_name="Patentamientos (EMA 12)")
    patentamientos_ema_24 = models.FloatField(verbose_name="Patentamientos (EMA 24)")
    patentamientos_delta = models.FloatField(verbose_name="Patentamientos (Delta)")

    prendas_lag_1 = models.FloatField(verbose_name="Prendas (Lag 1)")
    prendas_lag_2 = models.FloatField(verbose_name="Prendas (Lag 2)")
    prendas_lag_3 = models.FloatField(verbose_name="Prendas (Lag 3)")
    prendas_lag_6 = models.FloatField(verbose_name="Prendas (Lag 6)")
    prendas_ema_3 = models.FloatField(verbose_name="Prendas (EMA 3)")
    prendas_ema_6 = models.FloatField(verbose_name="Prendas (EMA 6)")
    prendas_ema_12 = models.FloatField(verbose_name="Prendas (EMA 12)")
    prendas_delta = models.FloatField(verbose_name="Prendas (Delta)")

    tasa_de_interes_lag_1 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 1)")
    tasa_de_interes_lag_2 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 2)")
    tasa_de_interes_lag_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 3)")
    tasa_de_interes_lag_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (Lag 6)")
    tasa_de_interes_ema_3 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 3)")
    tasa_de_interes_ema_6 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 6)")
    tasa_de_interes_ema_12 = models.FloatField(verbose_name="Tasa de Interés Préstamos (EMA 12)")
    tasa_de_interes_delta = models.FloatField(verbose_name="Tasa de Interés Préstamos (Delta)")

    tipo_de_cambio_lag_1 = models.FloatField(verbose_name="Tipo de Cambio (Lag 1)")
    tipo_de_cambio_lag_2 = models.FloatField(verbose_name="Tipo de Cambio (Lag 2)")
    tipo_de_cambio_lag_3 = models.FloatField(verbose_name="Tipo de Cambio (Lag 3)")
    tipo_de_cambio_lag_6 = models.FloatField(verbose_name="Tipo de Cambio (Lag 6)")
    tipo_de_cambio_ema_3 = models.FloatField(verbose_name="Tipo de Cambio (EMA 3)")
    tipo_de_cambio_ema_6 = models.FloatField(verbose_name="Tipo de Cambio (EMA 6)")
    tipo_de_cambio_ema_12 = models.FloatField(verbose_name="Tipo de Cambio (EMA 12)")
    tipo_de_cambio_delta = models.FloatField(verbose_name="Tipo de Cambio (Delta)")

    # Variables de Tiempo (One-Hot Encoded)
    mes_1 = models.FloatField(default=0)
    mes_2 = models.FloatField(default=0)
    mes_3 = models.FloatField(default=0)
    mes_4 = models.FloatField(default=0)
    mes_5 = models.FloatField(default=0)
    mes_6 = models.FloatField(default=0)
    mes_7 = models.FloatField(default=0)
    mes_8 = models.FloatField(default=0)
    mes_9 = models.FloatField(default=0)
    mes_10 = models.FloatField(default=0)
    mes_11 = models.FloatField(default=0)
    mes_12 = models.FloatField(default=0)

    semana_1 = models.FloatField(default=0)
    semana_2 = models.FloatField(default=0)
    semana_3 = models.FloatField(default=0)
    semana_4 = models.FloatField(default=0)
    semana_5 = models.FloatField(default=0)
    semana_6 = models.FloatField(default=0)
    semana_7 = models.FloatField(default=0)
    semana_8 = models.FloatField(default=0)
    semana_9 = models.FloatField(default=0)
    semana_10 = models.FloatField(default=0)
    semana_11 = models.FloatField(default=0)
    semana_12 = models.FloatField(default=0)
    semana_13 = models.FloatField(default=0)
    semana_14 = models.FloatField(default=0)
    semana_15 = models.FloatField(default=0)
    semana_16 = models.FloatField(default=0)
    semana_17 = models.FloatField(default=0)
    semana_18 = models.FloatField(default=0)
    semana_19 = models.FloatField(default=0)
    semana_20 = models.FloatField(default=0)
    semana_21 = models.FloatField(default=0)
    semana_22 = models.FloatField(default=0)
    semana_23 = models.FloatField(default=0)
    semana_24 = models.FloatField(default=0)
    semana_25 = models.FloatField(default=0)
    semana_26 = models.FloatField(default=0)
    semana_27 = models.FloatField(default=0)
    semana_28 = models.FloatField(default=0)
    semana_28 = models.FloatField(default=0)
    semana_29 = models.FloatField(default=0)
    semana_30 = models.FloatField(default=0)
    semana_31 = models.FloatField(default=0)
    semana_32 = models.FloatField(default=0)
    semana_33 = models.FloatField(default=0)
    semana_34 = models.FloatField(default=0)
    semana_35 = models.FloatField(default=0)
    semana_36 = models.FloatField(default=0)
    semana_37 = models.FloatField(default=0)
    semana_38 = models.FloatField(default=0)
    semana_39 = models.FloatField(default=0)
    semana_40 = models.FloatField(default=0)
    semana_41 = models.FloatField(default=0)
    semana_42 = models.FloatField(default=0)
    semana_43 = models.FloatField(default=0)
    semana_44 = models.FloatField(default=0)
    semana_45 = models.FloatField(default=0)
    semana_46 = models.FloatField(default=0)
    semana_47 = models.FloatField(default=0)
    semana_48 = models.FloatField(default=0)
    semana_49 = models.FloatField(default=0)
    semana_50 = models.FloatField(default=0)
    semana_51 = models.FloatField(default=0)
    semana_52 = models.FloatField(default=0)

    trimestre_1 = models.FloatField(default=0)
    trimestre_2 = models.FloatField(default=0)
    trimestre_3 = models.FloatField(default=0)
    trimestre_4 = models.FloatField(default=0)

    # Eventos y Características Adicionales
    es_semana_feriado = models.BooleanField(verbose_name="Es Semana Feriada")
    hubo_venta = models.BooleanField(verbose_name="Hubo Venta")
    dias_hasta_feriado = models.IntegerField(verbose_name="Días Hasta Feriado")

    # Historial de Ventas (Lagged)
    ventas_t_1 = models.FloatField(verbose_name="Ventas (t-1)")
    ventas_t_2 = models.FloatField(verbose_name="Ventas (t-2)")
    ventas_t_3 = models.FloatField(verbose_name="Ventas (t-3)")
    ventas_t_4 = models.FloatField(verbose_name="Ventas (t-4)")
    ventas_t_5 = models.FloatField(verbose_name="Ventas (t-5)")
    ventas_t_6 = models.FloatField(verbose_name="Ventas (t-6)")
    ventas_t_7 = models.FloatField(verbose_name="Ventas (t-7)")
    ventas_t_8 = models.FloatField(verbose_name="Ventas (t-8)")
    ventas_t_9 = models.FloatField(verbose_name="Ventas (t-9)")
    ventas_t_10 = models.FloatField(verbose_name="Ventas (t-10)")
    ventas_t_11 = models.FloatField(verbose_name="Ventas (t-11)")
    ventas_t_12 = models.FloatField(verbose_name="Ventas (t-12)")
    ventas_t_13 = models.FloatField(verbose_name="Ventas (t-13)")
    ventas_t_14 = models.FloatField(verbose_name="Ventas (t-14)")
    ventas_t_15 = models.FloatField(verbose_name="Ventas (t-15)")
    ventas_t_16 = models.FloatField(verbose_name="Ventas (t-16)")
    ventas_t_17 = models.FloatField(verbose_name="Ventas (t-17)")
    ventas_t_18 = models.FloatField(verbose_name="Ventas (t-18)")
    ventas_t_19 = models.FloatField(verbose_name="Ventas (t-19)")
    ventas_t_20 = models.FloatField(verbose_name="Ventas (t-20)")
    ventas_t_21 = models.FloatField(verbose_name="Ventas (t-21)")
    ventas_t_22 = models.FloatField(verbose_name="Ventas (t-22)")
    ventas_t_23 = models.FloatField(verbose_name="Ventas (t-23)")
    ventas_t_24 = models.FloatField(verbose_name="Ventas (t-24)")
    ventas_t_25 = models.FloatField(verbose_name="Ventas (t-25)")
    ventas_t_26 = models.FloatField(verbose_name="Ventas (t-26)")
    ventas_t_27 = models.FloatField(verbose_name="Ventas (t-27)")
    ventas_t_28 = models.FloatField(verbose_name="Ventas (t-28)")
    ventas_t_29 = models.FloatField(verbose_name="Ventas (t-29)")
    ventas_t_30 = models.FloatField(verbose_name="Ventas (t-30)")
    ventas_t_31 = models.FloatField(verbose_name="Ventas (t-31)")
    ventas_t_32 = models.FloatField(verbose_name="Ventas (t-32)")
    ventas_t_33 = models.FloatField(verbose_name="Ventas (t-33)")
    ventas_t_34 = models.FloatField(verbose_name="Ventas (t-34)")
    ventas_t_35 = models.FloatField(verbose_name="Ventas (t-35)")
    ventas_t_36 = models.FloatField(verbose_name="Ventas (t-36)")
    ventas_t_37 = models.FloatField(verbose_name="Ventas (t-37)")
    ventas_t_38 = models.FloatField(verbose_name="Ventas (t-38)")
    ventas_t_39 = models.FloatField(verbose_name="Ventas (t-39)")
    ventas_t_40 = models.FloatField(verbose_name="Ventas (t-40)")
    ventas_t_41 = models.FloatField(verbose_name="Ventas (t-41)")
    ventas_t_42 = models.FloatField(verbose_name="Ventas (t-42)")
    ventas_t_43 = models.FloatField(verbose_name="Ventas (t-43)")
    ventas_t_44 = models.FloatField(verbose_name="Ventas (t-44)")
    ventas_t_45 = models.FloatField(verbose_name="Ventas (t-45)")
    ventas_t_46 = models.FloatField(verbose_name="Ventas (t-46)")
    ventas_t_47 = models.FloatField(verbose_name="Ventas (t-47)")
    ventas_t_48 = models.FloatField(verbose_name="Ventas (t-48)")
    ventas_t_49 = models.FloatField(verbose_name="Ventas (t-49)")
    ventas_t_50 = models.FloatField(verbose_name="Ventas (t-50)")
    ventas_t_51 = models.FloatField(verbose_name="Ventas (t-51)")
    ventas_t_52 = models.FloatField(verbose_name="Ventas (t-52)")

    # Estadísticas de Ventas
    media_ultimas_4 = models.FloatField(verbose_name="Media Últimas 4 Semanas")
    std_pasada_4_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 4 Semanas")
    coef_var_4 = models.FloatField(verbose_name="Coeficiente de Variación 4 Semanas")

    media_ultimas_8 = models.FloatField(verbose_name="Media Últimas 8 Semanas")
    std_pasada_8_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 8 Semanas")
    coef_var_8 = models.FloatField(verbose_name="Coeficiente de Variación 8 Semanas")

    media_ultimas_12 = models.FloatField(verbose_name="Media Últimas 12 Semanas")
    std_pasada_12_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 12 Semanas")
    coef_var_12 = models.FloatField(verbose_name="Coeficiente de Variación 12 Semanas")

    media_ultimas_26 = models.FloatField(verbose_name="Media Últimas 26 Semanas")
    std_pasada_26_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 26 Semanas")
    coef_var_26 = models.FloatField(verbose_name="Coeficiente de Variación 26 Semanas")

    media_ultimas_52 = models.FloatField(verbose_name="Media Últimas 52 Semanas")
    std_pasada_52_semanas = models.FloatField(verbose_name="Desviación Estándar Últimas 52 Semanas")
    coef_var_52 = models.FloatField(verbose_name="Coeficiente de Variación 52 Semanas")

    def __str__(self):
        return f"{self.numero_parte} - {self.fecha}"