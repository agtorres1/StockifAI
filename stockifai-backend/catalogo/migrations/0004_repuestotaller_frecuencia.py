from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0003_repuestotaller_pred_1_repuestotaller_pred_2_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='repuestotaller',
            name='frecuencia',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
