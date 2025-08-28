



import os
from django.test import TestCase
from django.conf import settings
from miapp.models import Producto
from miapp.etl import procesar_excel  # tu función ETL

class ETLTests(TestCase):

    def setUp(self):
        # Ruta a un Excel de prueba que guardaste en `miapp/tests/files/ejemplo.xlsx`
        self.excel_path = os.path.join(settings.BASE_DIR, "miapp", "tests", "files", "ejemplo.xlsx")

    def test_etl_importa_excel(self):
        # Ejecutar tu ETL
        procesar_excel(self.excel_path)

        # Verificar que los datos se cargaron
        productos = Producto.objects.all()
        self.assertEqual(productos.count(), 3)  # por ej. esperás 3 productos en el Excel

        # Chequear un registro en particular
        p = Producto.objects.get(codigo="ABC123")
        self.assertEqual(p.nombre, "Lapicera Azul")
        self.assertEqual(p.stock, 50)
