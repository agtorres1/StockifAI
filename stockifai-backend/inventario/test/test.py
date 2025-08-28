import os
from django.test import TestCase
from inventario.services.import_catalogo import importar_catalogo   # Ajusta si tu función está en otro módulo

class ImportarCatalogoTest(TestCase):
    def test_importar_excel(self):
        # Construimos la ruta absoluta al archivo
        excel_path = os.path.join(
            os.path.dirname(__file__),  # carpeta donde está el test
            '..', '..', 'media', 'Demo catalogo.xlsx'  # sube dos niveles y entra a media/
        )
        excel_path = os.path.abspath(excel_path)

        # Llamamos a la función ETL
        result = importar_catalogo(file=excel_path)

        # Mostramos el resultado para debug
        print(result)

        # Opcional: algunos asserts básicos para verificar que el ETL funcionó
        self.assertIn("creados", result)
        self.assertIn("actualizados", result)
        self.assertIn("ignorados", result)
        self.assertIn("rechazados", result)
        self.assertEqual(result["mode"], "upsert")
