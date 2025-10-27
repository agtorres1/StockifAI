



class MiembroGrupo(models.Model):
    ROLES = [
        ('admin', 'Administrador'),  # ← Owner y Admin unificados
        ('member', 'Miembro'),
        ('viewer', 'Observador'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROLES, default='member')
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['usuario', 'grupo']