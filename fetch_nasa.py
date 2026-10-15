import json
import os
import random
from datetime import timedelta
from datetime import date
from pathlib import Path

import requests

API_KEY = os.environ["NASA_API_KEY"]
START = date(1995, 6, 16)
TODAY = date.today()
random_day = START + timedelta(days=random.randint(0, (TODAY - START).days))
URL = "https://api.nasa.gov/planetary/apod"

response = requests.get(
    URL,
    params={"api_key": API_KEY, "date": random_day.isoformat()},
    timeout=30,
)
response.raise_for_status()
entry = response.json()
if not isinstance(entry, dict) or not entry.get("url"):
    raise RuntimeError("NASA APOD did not return a usable entry.")
data = {
    "title": entry.get("title", ""),
    "date": entry.get("date", TODAY),
    "explanation": entry.get("explanation", ""),
    "url": entry.get("url", ""),
    "hdurl": entry.get("hdurl", ""),
    "media_type": entry.get("media_type", "image"),
    "copyright": entry.get("copyright", ""),
}
Path("nasa-today.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"Saved NASA APOD entry: {data['title']} ({data['date']})")

