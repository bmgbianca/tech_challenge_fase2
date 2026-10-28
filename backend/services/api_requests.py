import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

openrouteservice_key = os.environ["OPENROUTESERVICE_API_KEY"]

url = "https://api.heigit.org/openrouteservice/v2/matrix/driving-hgv"

headers = {"Authorization": openrouteservice_key, "Content-Type": "application/json"}


def fetch_distances(cities):

    try:
        response = requests.post(
            url,
            headers=headers,
            json={
                "locations": cities,
                "metrics": ["distance", "duration"],
                "units": "km",
            },
        )

        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching distances: {e}")
