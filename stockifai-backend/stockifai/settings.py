import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
AUTH_USER_MODEL = 'user.User'  # 'user' es el nombre de tu app
import environ

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-unsafe")
#DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("1","true","yes","y")
DEBUG = True  # ← CAMBIAR A TRUE TEMPORALMENTE

ALLOWED_HOSTS = ["*"] if DEBUG else os.getenv("DJANGO_ALLOWED_HOSTS","").split(",")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_crontab",
    "catalogo",
    "inventario",
    "corsheaders",
    "user",
    'd_externo',
    'django_extensions'
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'user.middleware.Auth0Middleware',
    #"auth0_backend.middleware.jwt_middleware"
]
ROOT_URLCONF = "stockifai.urls"

TEMPLATES = [{
    "BACKEND":"django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "stockifai-frontend"],
    "APP_DIRS":True,
    "OPTIONS":{"context_processors":[
        "django.template.context_processors.debug","django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]},
}]
WSGI_APPLICATION = "stockifai.wsgi.application"

def _env_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def _optional_int(value: Optional[str]):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _remove_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


db_target = (os.getenv("DB_TARGET", "aws") or "aws").strip().lower()
if db_target not in {"aws", "local"}:
    db_target = "aws"

aws_database_config = {
    'ENGINE': os.getenv('DB_ENGINE_AWS', 'dj_db_conn_pool.backends.mysql'),
    'NAME': os.getenv('DB_NAME_AWS', os.getenv('DB_NAMEAWS')),
    'USER': os.getenv('DB_USER_AWS', os.getenv('DB_USERAWS')),
    'PASSWORD': os.getenv('DB_PASSWORD_AWS', os.getenv('DB_PASSWORDAWS')),
    'HOST': os.getenv('DB_HOST_AWS', os.getenv('DB_HOSTAWS')),
    'PORT': os.getenv('DB_PORT_AWS', os.getenv('DB_PORTAWS')),
    'CONN_MAX_AGE': _optional_int(os.getenv('DB_CONN_MAX_AGE_AWS')) or 1800,
    'CONN_HEALTH_CHECKS': _env_bool(os.getenv('DB_CONN_HEALTH_CHECKS_AWS'), True),
    'OPTIONS': {
        'connect_timeout': _optional_int(os.getenv('DB_CONNECT_TIMEOUT_AWS')) or 10,
        'read_timeout': _optional_int(os.getenv('DB_READ_TIMEOUT_AWS')) or 600,
        'write_timeout': _optional_int(os.getenv('DB_WRITE_TIMEOUT_AWS')) or 600,
        'init_command': os.getenv('DB_INIT_COMMAND_AWS', "SET SESSION sql_mode='TRADITIONAL', autocommit=1, net_write_timeout=60, net_read_timeout=60"),
        'charset': os.getenv('DB_CHARSET_AWS', 'utf8mb4'),
        'sql_mode': os.getenv('DB_SQL_MODE_AWS', 'TRADITIONAL'),
        'isolation_level': os.getenv('DB_ISOLATION_LEVEL_AWS', 'READ COMMITTED'),
    },
    'POOL_OPTIONS': {
        'POOL_SIZE': _optional_int(os.getenv('DB_POOL_SIZE_AWS')) or 10,
        'MAX_OVERFLOW': _optional_int(os.getenv('DB_POOL_MAX_OVERFLOW_AWS')) or 20,
        'PRE_PING': _env_bool(os.getenv('DB_POOL_PRE_PING_AWS'), True),
        'POOL_TIMEOUT': _optional_int(os.getenv('DB_POOL_TIMEOUT_AWS')) or 30,
        'POOL_RECYCLE': _optional_int(os.getenv('DB_POOL_RECYCLE_AWS')) or 1800,
    },
}

local_database_config = {
    'ENGINE': os.getenv('DB_ENGINE_LOCAL', 'django.db.backends.mysql'),
    'NAME': os.getenv('DB_NAME_LOCAL', os.getenv('DB_NAME')),
    'USER': os.getenv('DB_USER_LOCAL', os.getenv('DB_USER')),
    'PASSWORD': os.getenv('DB_PASSWORD_LOCAL', os.getenv('DB_PASSWORD')),
    'HOST': os.getenv('DB_HOST_LOCAL', os.getenv('DB_HOST', '127.0.0.1')),
    'PORT': os.getenv('DB_PORT_LOCAL', os.getenv('DB_PORT', '3306')),
    'CONN_MAX_AGE': _optional_int(os.getenv('DB_CONN_MAX_AGE_LOCAL')),
    'CONN_HEALTH_CHECKS': _env_bool(os.getenv('DB_CONN_HEALTH_CHECKS_LOCAL')) if os.getenv('DB_CONN_HEALTH_CHECKS_LOCAL') is not None else None,
}


local_options = {
    'connect_timeout': _optional_int(os.getenv('DB_CONNECT_TIMEOUT_LOCAL')),
    'read_timeout': _optional_int(os.getenv('DB_READ_TIMEOUT_LOCAL')),
    'write_timeout': _optional_int(os.getenv('DB_WRITE_TIMEOUT_LOCAL')),
    'init_command': os.getenv('DB_INIT_COMMAND_LOCAL'),
    'charset': os.getenv('DB_CHARSET_LOCAL'),
    'sql_mode': os.getenv('DB_SQL_MODE_LOCAL'),
    'isolation_level': os.getenv('DB_ISOLATION_LEVEL_LOCAL'),
}

local_pool_options = {
    'POOL_SIZE': _optional_int(os.getenv('DB_POOL_SIZE_LOCAL')),
    'MAX_OVERFLOW': _optional_int(os.getenv('DB_POOL_MAX_OVERFLOW_LOCAL')),
    'PRE_PING': _env_bool(os.getenv('DB_POOL_PRE_PING_LOCAL')) if os.getenv('DB_POOL_PRE_PING_LOCAL') is not None else None,
    'POOL_TIMEOUT': _optional_int(os.getenv('DB_POOL_TIMEOUT_LOCAL')),
    'POOL_RECYCLE': _optional_int(os.getenv('DB_POOL_RECYCLE_LOCAL')),
}

if any(value is not None for value in local_options.values()):
    local_database_config['OPTIONS'] = _remove_none(local_options)

if any(value is not None for value in local_pool_options.values()):
    local_database_config['POOL_OPTIONS'] = _remove_none(local_pool_options)

DATABASES = {
    'default': _remove_none(aws_database_config if db_target == 'aws' else local_database_config),

}


LANGUAGE_CODE="es-ar"; TIME_ZONE="America/Argentina/Buenos_Aires"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"

ALLOW_AUTO_CREATE_REPUESTO=os.getenv("ALLOW_AUTO_CREATE_REPUESTO","False").lower() in ("1","true","yes","y")
PERMITIR_STOCK_NEGATIVO=os.getenv("PERMITIR_STOCK_NEGATIVO","False").lower() in ("1","true","yes","y")
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]
CORS_ALLOW_CREDENTIALS = True



REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'user.authentication.SessionAuthentication',  # ← AGREGAR ESTO
    ],


    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}





#REST_FRAMEWORK = {
#    'DEFAULT_AUTHENTICATION_CLASSES': (
#        'rest_framework_simplejwt.authentication.JWTAuthentication',
#    ),
#}


#REST_FRAMEWORK = {
#    'DEFAULT_AUTHENTICATION_CLASSES': (
#        'rest_framework.authentication.SessionAuthentication',
#    ),
#    'DEFAULT_PERMISSION_CLASSES': (
#        'rest_framework.permissions.AllowAny',
#    ),
#}

LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'import_debug.log',
        },
        'console': {  # ← AGREGAR ESTO
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'django.request': {  # ← AGREGAR ESTO
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}

##########codigo del auth0
# Inicializar django-environ
env = environ.Env()

# Ruta al archivo .env (está un nivel arriba de settings.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

AUTH0_DOMAIN = env('AUTH0_DOMAIN')
AUTH0_CLIENT_ID = env('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = env('AUTH0_CLIENT_SECRET')
AUTH0_AUDIENCE = env('AUTH0_AUDIENCE')
ALGORITHMS = env.list('AUTH0_ALGORITHMS')
AUTH0_CALLBACK_URL = "http://127.0.0.1:8000/api/callback/"
AUTH0_MGMT_CLIENT_ID = env("AUTH0_MGMT_CLIENT_ID")
AUTH0_MGMT_CLIENT_SECRET = env("AUTH0_MGMT_CLIENT_SECRET")
AUTH0_MGMT_AUDIENCE = env("AUTH0_MGMT_AUDIENCE")
AUTH0_MGMT_GRANT_TYPE = env("AUTH0_MGMT_GRANT_TYPE")

#####


CRONJOBS = [
    # Domingo 23:00 → corre el management command 'forecast_all'
    ('0 23 * * 0', 'django.core.management.call_command', ['forecast_all']),

    # TEST CADA 5 MIN PARA PROBAR
    #('*/5 * * * *', 'django.core.management.call_command', ['forecast_all']),
]

CRONTAB_COMMAND_SUFFIX = '>> /Users/gonzalo/Documents/StockifAI/stockifai-backend/logs/forecast_cron.log 2>&1'



