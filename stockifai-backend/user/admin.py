from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from user.api.models.models import User, Taller, Grupo, Direccion


# Registrar Direccion
@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ['id_direccion', 'calle', 'ciudad', 'codigo_postal', 'pais']
    search_fields = ['calle', 'ciudad', 'codigo_postal', 'pais']


# Registrar Taller
@admin.register(Taller)
class TallerAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'direccion', 'telefono', 'email', 'direccion_validada']  # ← Quité 'ciudad'
    search_fields = ['nombre', 'direccion', 'email']
    list_filter = ['direccion_validada']
    readonly_fields = ['direccion_normalizada', 'telefono_e164', 'latitud', 'longitud']


# Registrar Grupo
@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ['id_grupo', 'nombre', 'grupo_padre']
    search_fields = ['nombre', 'descripcion']
    list_filter = ['grupo_padre']


# Registrar User
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = [
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'taller',
        'grupo',
        'rol_en_grupo',
        'telefono',
        'is_staff',
        'is_superuser',
        'is_active'
    ]

    list_filter = [
        'is_staff',
        'is_superuser',
        'is_active',
        'taller',
        'grupo',
        'rol_en_grupo'
    ]

    search_fields = ['username', 'email', 'first_name', 'last_name', 'telefono']
    ordering = ['-id']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Asignaciones y Contacto', {
            'fields': ('taller', 'grupo', 'rol_en_grupo', 'direccion', 'telefono')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información adicional', {
            'fields': ('email', 'first_name', 'last_name', 'taller', 'grupo', 'rol_en_grupo', 'telefono')
        }),
    )