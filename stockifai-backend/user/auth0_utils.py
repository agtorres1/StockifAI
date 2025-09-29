# user/auth0_utils.py
import requests
from django.conf import settings

def get_mgmt_token():
    url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    payload = {
        "client_id": settings.AUTH0_CLIENT_ID,
        "client_secret": settings.AUTH0_CLIENT_SECRET,
        "audience": f"https://{settings.AUTH0_DOMAIN}/api/v2/",
        "grant_type": "client_credentials"
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    data = r.json()
    print("🔐 MGMT TOKEN:", data)  # 👈 Agregá esto
    return data["access_token"]

