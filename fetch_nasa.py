
import json
from pathlib import Path

import requests

API_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic/"
OUTPUT_FILE = Path(__file__).with_name("nasa-today.json")
MAX_ATTEMPTS = 10


def main():
    with requests.Session() as session:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = session.get(
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
                if not isinstance(entry, dict):
                    continue

                title = entry.get("title", "")
                if not isinstance(title, str):
                    continue
                title = title.strip()

                date = entry.get("date", "")
                explanation = entry.get("explanation", "")
                if not isinstance(explanation, str):
                    explanation = ""
                explanation = explanation.strip()

                media_type = entry.get("media_type", "")
                image_url = entry.get("hdurl") or entry.get("url", "")

                if not isinstance(image_url, str):
                    continue
                image_url = image_url.strip()

                if (
                    title
                    and title.lower() != "nasa science"
                    and date
                    and explanation
                    and media_type == "image"
                    and image_url.startswith("https://")
                    and "nasa-logo" not in image_url.lower()
                ):
                    cleaned_entry = {
                        "title": title,
                        "date": date,
                        "year": date[:4],
                        "explanation": explanation,
                        "url": image_url,
                        "media_type": "image",
                        "copyright": entry.get("copyright", ""),
                        "credit": entry.get("credit", ""),
                    }

                    OUTPUT_FILE.write_text(
                        json.dumps(cleaned_entry, indent=2),
                        encoding="utf-8",
                    )
                    print(f"Saved random NASA picture: {title} ({date})")
                    return

            print(
                f"Attempt {attempt}/{MAX_ATTEMPTS}: "
                "No valid image returned; trying again."
            )

    raise RuntimeError(
        "NASA did not return a valid random astronomy picture after "
        f"{MAX_ATTEMPTS} attempts. The existing picture file was left unchanged."
    )


if __name__ == "__main__":
    main()


