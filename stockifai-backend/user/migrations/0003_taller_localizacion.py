# Generated manually to añadir campos de localización y jerarquía de grupos
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0002_remove_direccion_pais"),
    ]

    operations = [
        migrations.AddField(
            model_name="taller",
            name="direccion_normalizada",
            field=models.CharField(blank=True, default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="taller",
            name="direccion_validada",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="taller",
            name="telefono_e164",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="taller",
            name="latitud",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="taller",
            name="longitud",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="grupo",
            name="grupo_padre",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="subgrupos", to="user.grupo"),
        ),
    ]
