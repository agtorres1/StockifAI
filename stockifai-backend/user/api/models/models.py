import logging
from typing import Optional, Tuple

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from user.services.direcciones import (
    geocodificar_direccion,
    normalizar_direccion,
    normalizar_telefono,
)

logger = logging.getLogger(__name__)


class Direccion(models.Model):
    id_direccion = models.AutoField(primary_key=True)
    calle = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    pais = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.calle}, {self.ciudad}"


class Taller(models.Model):
    nombre = models.CharField(max_length=120)
    direccion = models.CharField(max_length=255, blank=True)
    direccion_normalizada = models.CharField(max_length=255, blank=True)
    direccion_validada = models.BooleanField(default=False)
    telefono = models.CharField(max_length=50, blank=True)
    telefono_e164 = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        direccion_original = self.direccion or ""
        direccion_normalizada, es_valida, _ = normalizar_direccion(direccion_original)

        if direccion_normalizada:
            self.direccion_normalizada = direccion_normalizada
        else:
            self.direccion_normalizada = direccion_original.strip()

        self.direccion_validada = es_valida

        # Normaliza el teléfono local y E164 (si hay número)
        telefono_local, telefono_e164 = normalizar_telefono(self.telefono)
        if telefono_local:
            self.telefono = telefono_local
        if telefono_e164:
            self.telefono_e164 = telefono_e164

        # Recalcula geolocalización solo si hace falta
        should_geocode = False
        direccion_a_geocodificar = self.direccion_normalizada or direccion_original.strip()

        if direccion_a_geocodificar:
            if self.pk:
                try:
                    anterior = Taller.objects.get(pk=self.pk)
                    direccion_cambio = anterior.direccion_normalizada != self.direccion_normalizada
                    if direccion_cambio:
                        should_geocode = True
                        # si la dirección cambió, descartamos coordenadas viejas
                        self.latitud = None
                        self.longitud = None
                except Taller.DoesNotExist:
                    should_geocode = True
            else:
                should_geocode = True

        if should_geocode and es_valida and (self.latitud is None or self.longitud is None):
            try:
                coords: Optional[Tuple[float, float]] = geocodificar_direccion(direccion_a_geocodificar)
            except Exception as exc:
                logger.warning("Error geocodificando dirección '%s': %s", direccion_a_geocodificar, exc)
                coords = None

            if coords:
                self.latitud, self.longitud = coords

        super().save(*args, **kwargs)


class Grupo(models.Model):
    id_grupo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    grupo_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subgrupos'
    )

    def __str__(self):
        return self.nombre


class GrupoTaller(models.Model):
    id_grupo_taller = models.AutoField(primary_key=True)
    id_grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    id_taller = models.ForeignKey(Taller, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id_grupo.nombre} - {self.id_taller.nombre}"


class User(AbstractUser):
    ROLES_EN_GRUPO = [
        ('admin', 'Administrador del Grupo'),
        ('member', 'Miembro'),
        ('viewer', 'Observador'),
    ]

    taller = models.ForeignKey(
        Taller,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    direccion = models.OneToOneField(
        Direccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    telefono = models.CharField(max_length=20, blank=True)
    rol_en_grupo = models.CharField(
        max_length=20,
        choices=ROLES_EN_GRUPO,
        default='member',
        blank=True,
        null=True,
        help_text="Solo aplica si pertenece a un grupo"
    )

    class Meta:
        db_table = 'custom_user'

    def __str__(self):
        return self.username

    def clean(self):
        """Validar que no tenga taller Y grupo al mismo tiempo"""
        if self.taller and self.grupo:
            raise ValidationError(
                "Un usuario no puede pertenecer a un taller individual Y a un grupo al mismo tiempo. "
                "Debe elegir uno u otro."
            )

        # Validar que si tiene grupo, debe tener rol_en_grupo
        if self.grupo and not self.rol_en_grupo:
            raise ValidationError(
                "Si el usuario pertenece a un grupo, debe tener un rol asignado."
            )

        # Validar que si tiene taller, NO debe tener rol_en_grupo
        if self.taller and self.rol_en_grupo:
            self.rol_en_grupo = None

    def save(self, *args, **kwargs):
        """Ejecutar validación antes de guardar"""
        self.clean()
        super().save(*args, **kwargs)