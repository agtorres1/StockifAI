# Guía rápida para levantar el backend

## 1. Prerrequisitos
- Python 3.12 y pip.
- MySQL 8 (local o remoto) con un schema vacío llamado `stockifai` y un usuario con permisos sobre ese schema (en los ejemplos se usa `root`).


## 2. Crear el entorno y dependencias
```bash
python -3.12 -m venv .venv
source .venv/bin/activate  # Windows Powershell (La terminal de pycharm es powershell) usar:
.venv\Scripts\Activate.ps1

luego:
pip install -r requirements.txt
```

## 3. Configurar las variables de entorno
1. Copiá el archivo `.env` incluido en el repo (o `.env.example` si existiera) y completá los valores locales.
2. Asegurate de establecer `DB_TARGET=local` para que Django use la configuración que apunta a tu base de datos local.
3. Ajustá `DB_NAME_LOCAL`, `DB_USER_LOCAL`, `DB_PASSWORD_LOCAL`, `DB_HOST_LOCAL` y `DB_PORT_LOCAL` según tus credenciales. Si usás sockets o puertos distintos, también podés definir los overrides opcionales (`DB_CONNECT_TIMEOUT_LOCAL`, `DB_CHARSET_LOCAL`, etc.).


## 4. Inicializar la base vacía
Con la base local vacía **no hace falta** correr `makemigrations` (ya están versionadas en el repo). Sólo ejecutá las migraciones existentes para crear toda la estructura de tablas:
```bash
python manage.py migrate
```

El comando anterior aplica automáticamente todas las migraciones incluidas, como la que agrega los campos de geolocalización al modelo `Taller`.

### ¿Qué es una migración y cuándo necesito `makemigrations`?

- **Migraciones**: son archivos versionados (en la carpeta `*/migrations`) que describen cómo debe evolucionar el esquema de la base de datos. Cada vez que alguien modifica un modelo, ejecuta `python manage.py makemigrations` en su entorno local para generar el archivo y lo comitea al repositorio.
- **`makemigrations`** sólo se usa cuando hacés un cambio nuevo a un modelo y necesitás crear *nuevas* migraciones. Si solo estás actualizando tu copia del proyecto —local o en AWS— no tenés que volver a correrlo, porque ya existen en el repo.
- **`migrate`** aplica las migraciones existentes sobre la base seleccionada (`DB_TARGET`). Es el comando que debés ejecutar tanto en una base local vacía como en una base de AWS que ya tiene datos, para mantener el esquema sincronizado con el código.

> En entornos con datos productivos (por ejemplo, AWS) recordá hacer un respaldo antes de correr `python manage.py migrate`. Una vez aplicado, tus datos permanecen y sólo se ajusta la estructura de tablas.

## 5. Cargar datos de prueba (opcional)
Si querés usar los datos de ejemplo del localizador, guardá la semilla provista como `seed_localizador.json` y ejecutá:
```bash
python manage.py loaddata seed_localizador.json
```
Esto insertará talleres, grupos, repuestos y stock básico para probar el endpoint `/inventario/api/talleres/<taller_id>/localizador`.

## 6. Levantar el servidor de desarrollo
Finalmente iniciá el backend:
```bash
py manage.py runserver
```

Con estos pasos vas a tener el backend corriendo contra una base local recién inicializada, listo para que el front realice consultas de stock.