from rest_framework.exceptions import PermissionDenied
from user.models import GrupoTaller

class PermissionChecker:

    @staticmethod
    def puede_gestionar_grupo(user, grupo):
        # Admin general o superusuario
        if user.is_staff or user.is_superuser:
            return True

        # Admin del grupo específico
        if user.grupo == grupo and user.rol_en_grupo == 'admin':
            return True

        return False

    @staticmethod
    def puede_editar_taller(user, taller):
        """¿Puede EDITAR el taller?"""
        if user.is_staff or user.is_superuser:
            return True

        if taller.propietario == user:
            return True

        for grupo in taller.grupos.all():
            from user.roles import MiembroGrupo
            miembro = MiembroGrupo.objects.filter(
                usuario=user,
                grupo=grupo
            ).first()

            if miembro and miembro.rol == 'admin':
                return True

        return False


    @staticmethod
    def puede_eliminar_taller(user, taller):
        """¿Puede ELIMINAR el taller?"""
        if user.is_staff or user.is_superuser:
            return True

        # Importamos aquí para evitar dependencias circulares
        from user.models import GrupoTaller

        print(f"🧩 Entrando en puede_eliminar_taller")
        print(f"Usuario: {user.username} | ID: {user.id}")
        print(f"is_staff: {user.is_staff} | is_superuser: {user.is_superuser}")
        print(f"Grupo del usuario: {getattr(user.grupo, 'nombre', None)}")
        print(f"Rol del usuario en el grupo: {user.rol_en_grupo}")
        print(f"Taller que intenta eliminar: {taller.id}")

        # Verificamos si el taller está vinculado al grupo del usuario
        vinculo_existe = GrupoTaller.objects.filter(
            id_grupo=user.grupo_id,
            id_taller=taller.id
        ).exists()

        print(f"¿Existe vínculo grupo-taller? {vinculo_existe}")

        # ✅ Solo puede eliminar si es admin de ese grupo y el taller pertenece a su grupo
        puede = vinculo_existe and user.rol_en_grupo == "admin"

        print(f"¿Puede eliminar? {puede}")
        return puede

    @staticmethod
    def puede_gestionar_miembros(user, grupo):
        """¿Puede agregar/quitar miembros del grupo?"""
        if user.is_staff or user.is_superuser:
            return True

        from user.roles import MiembroGrupo
        miembro = MiembroGrupo.objects.filter(
            usuario=user,
            grupo=grupo
        ).first()

        return miembro and miembro.rol == 'admin'

    @staticmethod
    def puede_eliminar_grupo(user, grupo):
        """¿Puede eliminar el grupo?"""
        if user.is_staff or user.is_superuser:
            return True

        from user.roles import MiembroGrupo
        miembro = MiembroGrupo.objects.filter(
            usuario=user,
            grupo=grupo
        ).first()

        return miembro and miembro.rol == 'admin'

    # ===== NUEVOS MÉTODOS =====

    @staticmethod
    def get_user_from_session(request):
        """Obtiene el usuario de la sesión"""
        user_id = request.session.get('user_id')
        if not user_id:
            raise PermissionDenied("No autenticado")

        try:
            from user.api.models.models import User
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise PermissionDenied("Usuario no encontrado")

    @staticmethod
    def filter_repuestos_queryset(queryset, user):
        """Filtra repuestos según permisos del usuario"""
        # Superuser ve TODO
        if user.is_superuser or user.is_staff:
            return queryset

        # Sin taller ni grupo = logs por ahora
        if not user.taller and not user.grupo:
            print(f"⚠️ Usuario {user.email} sin taller ni grupo accediendo a repuestos")
            return queryset  # Por ahora no bloqueamos

        # Con taller: solo repuestos de su taller
        if user.taller:
            from catalogo.models import RepuestoTaller
            repuestos_ids = RepuestoTaller.objects.filter(
                taller=user.taller
            ).values_list('repuesto_id', flat=True)
            return queryset.filter(id__in=repuestos_ids)

        # Con grupo: TODO - definir lógica
        return queryset

    @staticmethod
    def puede_ver_taller(user, taller):
        """¿Puede VER el taller?"""
        # Admin del sistema
        if user.is_staff or user.is_superuser:
            return True

        # Su propio taller
        if user.taller and user.taller.id == taller.id:
            return True

        # Taller de su grupo
        if user.grupo:
            from user.api.models.models import GrupoTaller
            return GrupoTaller.objects.filter(
                id_grupo=user.grupo,
                id_taller=taller
            ).exists()

        return False

    @staticmethod
    def filter_repuestos_taller_queryset(queryset, user):
        """Filtra RepuestoTaller según permisos"""
        if user.is_superuser or user.is_staff:
            return queryset

        if not user.taller and not user.grupo:
            print(f"⚠️ Usuario {user.email} sin taller ni grupo accediendo a repuestos_taller")
            return queryset.none()  # O queryset según decidas

        if user.taller:
            return queryset.filter(taller=user.taller)

        # Con grupo: talleres del grupo
        if user.grupo:
            from user.api.models.models import GrupoTaller
            talleres_ids = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)
            return queryset.filter(taller_id__in=talleres_ids)

        return queryset.none()

    @staticmethod
    def filter_stock_queryset(queryset, user):
        """Filtra StockPorDeposito según permisos"""
        if user.is_superuser or user.is_staff:
            return queryset

        if not user.taller and not user.grupo:
            return queryset.none()

        if user.taller:
            return queryset.filter(repuesto_taller__taller=user.taller)

        if user.grupo:
            from user.api.models.models import GrupoTaller
            talleres_ids = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)
            return queryset.filter(repuesto_taller__taller_id__in=talleres_ids)

        return queryset.none()

    @staticmethod
    def filter_movimientos_queryset(queryset, user):
        """Filtra Movimiento según permisos"""
        if user.is_superuser or user.is_staff:
            return queryset

        if not user.taller and not user.grupo:
            return queryset.none()

        if user.taller:
            return queryset.filter(stock_por_deposito__repuesto_taller__taller=user.taller)

        if user.grupo:
            from user.api.models.models import GrupoTaller
            talleres_ids = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)
            return queryset.filter(stock_por_deposito__repuesto_taller__taller_id__in=talleres_ids)

        return queryset.none()

    @staticmethod
    def filter_depositos_queryset(queryset, user):
        """Filtra Deposito según permisos"""
        if user.is_superuser or user.is_staff:
            return queryset

        if not user.taller and not user.grupo:
            return queryset.none()

        if user.taller:
            return queryset.filter(taller=user.taller)

        if user.grupo:
            from user.api.models.models import GrupoTaller
            talleres_ids = GrupoTaller.objects.filter(
                id_grupo=user.grupo
            ).values_list('id_taller', flat=True)
            return queryset.filter(taller_id__in=talleres_ids)

        return queryset.none()

