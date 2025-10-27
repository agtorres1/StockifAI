from django.db import models
from django.contrib.auth.models import AbstractUser

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
    telefono = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Grupo(models.Model):
    id_grupo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()

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

    # ← IMPORTANTE: null=True, blank=True permite que sean NULL
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

    # ← VALIDACIÓN: No puede tener ambos al mismo tiempo
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
            self.rol_en_grupo = None  # Limpiar el rol si está en taller individual

    def save(self, *args, **kwargs):
        """Ejecutar validación antes de guardar"""
        self.clean()
        super().save(*args, **kwargs)

