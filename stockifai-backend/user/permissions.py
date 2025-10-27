

class PermissionChecker:

    @staticmethod
    def puede_editar_taller(user, taller):
        """¿Puede EDITAR el taller?"""

        if user.is_staff or user.is_superuser:
            return True


        if taller.propietario == user:
            return True

        
        for grupo in taller.grupos.all():
            miembro = MiembroGrupo.objects.filter(
                usuario=user,
                grupo=grupo
            ).first()

            if miembro and miembro.rol == 'admin':  # ← Solo admin
                return True

        return False

    @staticmethod
    def puede_eliminar_taller(user, taller):
        """¿Puede ELIMINAR el taller?"""
        # Admin del sistema
        if user.is_staff or user.is_superuser:
            return True

        # Propietario directo
        if taller.propietario == user:
            return True

        # Admin del grupo (antes solo owner, ahora admin)
        for grupo in taller.grupos.all():
            miembro = MiembroGrupo.objects.filter(
                usuario=user,
                grupo=grupo
            ).first()

            if miembro and miembro.rol == 'admin':  # ← Admin puede eliminar
                return True

        return False

    @staticmethod
    def puede_gestionar_miembros(user, grupo):
        """¿Puede agregar/quitar miembros del grupo?"""
        # Admin del sistema
        if user.is_staff or user.is_superuser:
            return True

        # Admin del grupo (antes owner o admin, ahora solo admin)
        miembro = MiembroGrupo.objects.filter(
            usuario=user,
            grupo=grupo
        ).first()

        return miembro and miembro.rol == 'admin'  # ← Solo admin

    @staticmethod
    def puede_eliminar_grupo(user, grupo):
        """¿Puede eliminar el grupo?"""
        # Admin del sistema
        if user.is_staff or user.is_superuser:
            return True

        # Admin del grupo (antes solo owner, ahora admin)
        miembro = MiembroGrupo.objects.filter(
            usuario=user,
            grupo=grupo
        ).first()

        return miembro and miembro.rol == 'admin'  # ← Admin puede eliminar