
import json
from pathlib import Path

import requests

API_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic/"
OUTPUT_FILE = Path(__file__).with_name("nasa-today.json")


def main():
    response = requests.get(
        API_URL,
        params={"count": 1},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if isinstance(result, list):
        entries = result
    else:
        entries = [result]

    for entry in entries:
        title = entry.get("title", "").strip()
        date = entry.get("date", "")
        explanation = entry.get("explanation", "").strip()
        media_type = entry.get("media_type", "")
        image_url = entry.get("hdurl") or entry.get("url", "")

        if (
            title
            and title.lower() != "nasa science"
            and date
            and explanation
            and media_type == "image"
            and image_url
            and "nasa-logo" not in image_url.lower()
        ):
            cleaned_entry = {
                "title": title,
                "date": date,
                "year": date[:4],
                "explanation": explanation,
                "url": image_url,
                "media_type": media_type,
                "copyright": entry.get("copyright", ""),
                "credit": entry.get("credit", ""),
            }

            OUTPUT_FILE.write_text(
                json.dumps(cleaned_entry, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {title} ({date})")
            return

    raise RuntimeError(
        "NASA did not return a valid astronomy picture. "
        "The existing picture file was left unchanged."
    )


if __name__ == "__main__":
    main()


