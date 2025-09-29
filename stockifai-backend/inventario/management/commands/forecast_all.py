from datetime import date, timedelta, datetime

from django.core.management.base import BaseCommand

from AI.services.forecast_pipeline import ejecutar_forecast_talleres


class Command(BaseCommand):
    help = "Ejecutar el forecast para TODOS los talleres, apuntando al próximo lunes."

    def handle(self, *args, **options):
        self.stdout.write(f"CRON TASK")
        fecha_lunes = next_monday_str()

        self.stdout.write(f"Ejecutando forecast para lunes {fecha_lunes}")

        result = ejecutar_forecast_talleres(fecha_lunes)

        self.stdout.write(self.style.SUCCESS("Forecast OK"))
        self.stdout.write(
            f"Talleres procesados: {len(result.get('ok', []))}, errores: {len(result.get('errores', []))}")


def next_monday_str() -> datetime:
    today = date.today()
    days = (7 - today.weekday()) % 7
    monday_date = today + timedelta(days=days)
    return datetime.combine(monday_date, datetime.min.time())