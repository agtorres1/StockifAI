import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-unsafe")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("1","true","yes","y")
ALLOWED_HOSTS = ["*"] if DEBUG else os.getenv("DJANGO_ALLOWED_HOSTS","").split(",")
INSTALLED_APPS = [
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "rest_framework","catalogo","inventario","corsheaders"
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "stockifai.urls"
TEMPLATES = [{
    "BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[], "APP_DIRS":True,
    "OPTIONS":{"context_processors":[
        "django.template.context_processors.debug","django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]},
}]
WSGI_APPLICATION = "stockifai.wsgi.application"
DATABASES = {"default":{
    "ENGINE":"django.db.backends.mysql","NAME":os.getenv("DB_NAME","stockifai"),
    "USER":os.getenv("DB_USER","root"),"PASSWORD":os.getenv("DB_PASSWORD",""),
    "HOST":os.getenv("DB_HOST","127.0.0.1"),"PORT":os.getenv("DB_PORT","3306"),
    "OPTIONS":{"charset":"utf8mb4"}
}}
LANGUAGE_CODE="es-ar"; TIME_ZONE="America/Argentina/Buenos_Aires"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
REST_FRAMEWORK={"DEFAULT_RENDERER_CLASSES":["rest_framework.renderers.JSONRenderer"],
"DEFAULT_PARSER_CLASSES":["rest_framework.parsers.JSONParser","rest_framework.parsers.FormParser","rest_framework.parsers.MultiPartParser"]}
ALLOW_AUTO_CREATE_REPUESTO=os.getenv("ALLOW_AUTO_CREATE_REPUESTO","False").lower() in ("1","true","yes","y")
PERMITIR_STOCK_NEGATIVO=os.getenv("PERMITIR_STOCK_NEGATIVO","False").lower() in ("1","true","yes","y")
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]
CORS_ALLOW_CREDENTIALS = True
