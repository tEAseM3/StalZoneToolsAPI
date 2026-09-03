import os

import requests
from dotenv import load_dotenv

load_dotenv()


def get_access_token():
    response = requests.post(
        "https://exbo.net/oauth/token",
        data={
            "client_id": os.getenv("STALZONE_CLIENT_ID"),
            "client_secret": os.getenv("STALZONE_CLIENT_SECRET"),
            "grant_type": "client_credentials",
            "scope": "",
        },
    )

    response.raise_for_status()

    return response.json()["access_token"]
