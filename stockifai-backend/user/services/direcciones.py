"""Utilidades de normalización y geocodificación para direcciones y teléfonos."""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, Optional, Tuple

try:  # pragma: no cover - import opcional para entornos sin geopy
    from geopy.exc import GeocoderServiceError
    from geopy.geocoders import Nominatim
except ModuleNotFoundError:  # pragma: no cover
    GeocoderServiceError = Exception  # type: ignore
    Nominatim = None  # type: ignore

logger = logging.getLogger(__name__)

_DEFAULT_COUNTRY = "Argentina"
_TELEFONO_REGEX = re.compile(r"\d+")


def normalizar_direccion(direccion: str) -> Tuple[str, bool, Dict[str, str]]:
    """Normaliza una dirección en texto libre.

    Devuelve una tupla ``(direccion_normalizada, es_valida, componentes)``.
    ``es_valida`` se considera True si la dirección contiene calle y número.
    ``componentes`` incluye datos detectados (calle, numero, ciudad, provincia).
    """

    if not direccion:
        return "", False, {}

    limpia = re.sub(r"\s+", " ", direccion).strip()
    if not limpia:
        return "", False, {}

    partes = [p.strip() for p in limpia.split(",") if p.strip()]
    normalizada = ", ".join(partes)

    componentes: Dict[str, str] = {}
    es_valida = False

    if partes:
        primera = partes[0]
        match = re.match(r"(?P<calle>[\w\s\.áéíóúÁÉÍÓÚñÑ]+?)\s+(?P<num>[0-9A-Za-z\-/]+)$", primera)
        if match:
            componentes["calle"] = match.group("calle").strip().title()
            componentes["numero"] = match.group("num")
            es_valida = True
        else:
            componentes["calle"] = primera.title()
            es_valida = bool(re.search(r"\d", primera))

    if len(partes) > 1:
        componentes["ciudad"] = partes[1].title()
    if len(partes) > 2:
        componentes["provincia"] = partes[2].title()

    return normalizada, es_valida, componentes


def normalizar_telefono(telefono: Optional[str]) -> Tuple[str, Optional[str]]:
    """Devuelve un teléfono legible localmente y su versión en formato E.164.

    El formato E.164 se calcula asumiendo números de Argentina (prefijo +54).
    """

    if not telefono:
        return "", None

    solo_digitos = "".join(_TELEFONO_REGEX.findall(telefono))
    if not solo_digitos:
        return telefono.strip(), None

    # Normaliza el número local (agrega guiones cada 4 dígitos para legibilidad simple)
    local = solo_digitos
    if len(local) >= 8:
        local = f"{local[:-4]}-{local[-4:]}"

    # Construimos E.164 (quita ceros iniciales)
    e164 = solo_digitos.lstrip("0")
    if not e164.startswith("54"):
        e164 = f"54{e164}"

    return local, e164


@lru_cache(maxsize=1)
def _get_geocoder() -> Optional[Nominatim]:
    if Nominatim is None:
        logger.debug("geopy no está instalado; se omite geocodificación")
        return None
    return Nominatim(user_agent="stockifai_localizador")


def geocodificar_direccion(direccion: str, *, pais: str = _DEFAULT_COUNTRY) -> Optional[Tuple[float, float]]:
    """Obtiene latitud y longitud utilizando OpenStreetMap vía geopy.

    En caso de error o falta de resultados devuelve ``None`` para evitar que la
    creación/edición de talleres falle.
    """

    geocoder = _get_geocoder()
    if geocoder is None:
        return None

    try:
        location = geocoder.geocode(f"{direccion}, {pais}", timeout=10)
    except GeocoderServiceError as exc:  # pragma: no cover - defensivo
        logger.warning("Fallo al geocodificar '%s': %s", direccion, exc)
        return None

    if not location:
        logger.info("No se encontraron coordenadas para '%s'", direccion)
        return None

    return float(location.latitude), float(location.longitude)
