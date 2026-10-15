
import json
import random
from pathlib import Path

import requests

API_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic/"
OUTPUT_FILE = Path(__file__).with_name("nasa-today.json")


def main():
    previous_date = None

    if OUTPUT_FILE.exists():
        try:
            previous = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            previous_date = previous.get("date")
        except (json.JSONDecodeError, OSError):
            pass

    response = requests.get(
        API_URL,
        params={"count": 25},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    entries = result if isinstance(result, list) else [result]
    candidates = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        title = entry.get("title", "")
        date = entry.get("date", "")
        explanation = entry.get("explanation", "")
        media_type = entry.get("media_type", "")
        image_url = entry.get("hdurl") or entry.get("url", "")

        if not all(isinstance(value, str) for value in (
            title, date, explanation, media_type, image_url
        )):
            continue

        title = title.strip()
        date = date.strip()
        explanation = explanation.strip()
        image_url = image_url.strip()

        if (
            title
            and title.lower() != "nasa science"
            and date
            and explanation
            and media_type == "image"
            and image_url.startswith("https://")
            and "nasa-logo" not in image_url.lower()
            and "/image-article/" not in image_url.lower()
        ):
            candidates.append({
                "title": title,
                "date": date,
                "year": date[:4],
                "explanation": explanation,
                "url": image_url,
                "media_type": "image",
                "copyright": entry.get("copyright", ""),
                "credit": entry.get("credit", ""),
            })

    if not candidates:
        raise RuntimeError(
            "NASA returned no valid images. Existing JSON was not changed."
        )

    alternatives = [
        entry for entry in candidates
        if entry["date"] != previous_date
    ]

    choices = alternatives or candidates
    selected = random.choice(choices)

    OUTPUT_FILE.write_text(
        json.dumps(selected, indent=2),
        encoding="utf-8",
    )

    print(
        f"Saved random NASA picture: "
        f"{selected['title']} ({selected['date']})"
    )


if __name__ == "__main__":
    main()
