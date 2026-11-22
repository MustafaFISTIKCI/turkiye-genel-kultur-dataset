"""Fetch commercially-safe, royalty-free images from Wikimedia Commons for 81 Turkish provinces x 3 categories."""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageOps

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "Turkiye81IlDatasetBot/1.0 (https://github.com/MustafaFISTIKCI/turkiye-81-il-dataset)"

ALLOWED_LICENSE_PREFIXES = (
    "cc0",
    "cc-zero",
    "public domain",
    "pd",
    "pdm",
    "cc by",
    "cc-by",
)
FORBIDDEN_LICENSE_TOKENS = ("nc", "nd", "fair", "copyright", "restricted", "unknown")

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "seed_locations.json"
DATASET_PATH = ROOT / "data" / "dataset.json"
MISSING_PATH = ROOT / "data" / "missing.json"
CREDITS_PATH = ROOT / "CREDITS.md"
IMAGES_DIR = ROOT / "images"


def clean_html(raw: str | None) -> str:
    if not raw:
        return "Bilinmiyor"
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120] if text else "Bilinmiyor"


def is_allowed_license(license_short: str) -> bool:
    norm = license_short.strip().lower()
    if not norm:
        return False
    # Reject any non-commercial, no-derivatives, or copyrighted licenses
    tokens = re.split(r"[\s\-_/]+", norm)
    if any(tok in FORBIDDEN_LICENSE_TOKENS for tok in tokens):
        return False
    return any(norm.startswith(prefix) for prefix in ALLOWED_LICENSE_PREFIXES)


def search_commons(session: requests.Session, query: str, limit: int = 8) -> list[dict[str, Any]]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": 6,  # File: namespace
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1280,
    }
    resp = session.get(COMMONS_API, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    return list(pages.values())


def score_candidate(page: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    title = page.get("title", "")
    # Skip maps, flags, logos, coats of arms, and scans
    lower_title = title.lower()
    if any(bad in lower_title for bad in ("map", "harita", "flag", "logo", "coat_of_arms", "location", "locator")):
        return None

    infos = page.get("imageinfo")
    if not infos:
        return None
    info = infos[0]

    mime = (info.get("mime") or "").lower()
    if mime not in ("image/jpeg", "image/png", "image/webp"):
        return None

    width = info.get("width") or 0
    height = info.get("height") or 0
    if width < 600 or height < 400:
        return None

    aspect = width / height
    if aspect < 0.75:  # skip tall vertical portraits
        return None

    ext = info.get("extmetadata") or {}
    lic_short = clean_html((ext.get("LicenseShortName") or {}).get("value"))
    if not is_allowed_license(lic_short):
        return None

    author = clean_html((ext.get("Artist") or {}).get("value"))
    source_url = info.get("descriptionurl") or ""
    download_url = info.get("thumburl") or info.get("url") or ""
    if not download_url or not source_url:
        return None

    score = 0
    if width > height:
        score += 20
    if 1.2 <= aspect <= 2.0:
        score += 15
    if width >= 1000:
        score += 5
    if lic_short.lower().startswith(("cc0", "public domain", "pd")):
        score += 5

    return score, {
        "title": title,
        "download_url": download_url,
        "source_url": source_url,
        "author": author,
        "license": lic_short,
        "orig_width": width,
        "orig_height": height,
    }


def find_best_image(session: requests.Session, queries: list[str], delay: float) -> dict[str, Any] | None:
    best: tuple[int, dict[str, Any]] | None = None
    for query in queries:
        try:
            pages = search_commons(session, query)
        except Exception as exc:
            print(f"    [WARN] Search failed for '{query}': {exc}")
            time.sleep(delay)
            continue

        for page in pages:
            scored = score_candidate(page)
            if scored is None:
                continue
            if best is None or scored[0] > best[0]:
                best = scored

        time.sleep(delay)
        if best and best[0] >= 40:
            break

    return best[1] if best else None


def download_and_save_webp(session: requests.Session, url: str, out_path: Path, max_width: int = 1200) -> tuple[int, int]:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > max_width:
        new_height = int(img.height * (max_width / img.width))
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="WEBP", quality=82, method=4)
    return img.width, img.height


def write_credits(entries: list[dict[str, Any]]) -> None:
    lines = [
        "# Görsel Atıfları ve Lisanslar (CREDITS)",
        "",
        "Bu veri setindeki tüm görseller [Wikimedia Commons](https://commons.wikimedia.org/) üzerinden yalnızca ticari kullanıma ve türev çalışmalara izin veren (`CC0`, `Public Domain`, `CC BY`, `CC BY-SA`) lisanslarla derlenmiştir.",
        "",
        f"Toplam Görsel: **{len(entries)}**",
        "",
        "| ID | İl | Kategori | Konum / Lezzet | Yazar | Lisans | Kaynak |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        author = e["author"].replace("|", "/")
        lic = e["license"].replace("|", "/")
        lines.append(
            f"| `{e['id']}` | {e['city']} | `{e['category']}` | {e['name']} | {author} | {lic} | [Wikimedia]({e['sourceUrl']}) |"
        )
    CREDITS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_outputs(entries: list[dict[str, Any]], missing: list[dict[str, Any]]) -> None:
    entries_sorted = sorted(entries, key=lambda x: x["id"])
    DATASET_PATH.write_text(json.dumps(entries_sorted, ensure_ascii=False, indent=2), encoding="utf-8")
    MISSING_PATH.write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")
    write_credits(entries_sorted)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Wikimedia Commons images for Turkey 81 provinces dataset.")
    parser.add_argument("--limit", type=int, default=0, help="Max items to process (0 = all)")
    parser.add_argument("--resume", action="store_true", help="Skip items already present in data/dataset.json")
    parser.add_argument("--category", type=str, default="", help="Filter by category (tarihi_yapi, doga, yemek)")
    parser.add_argument("--plate", type=str, default="", help="Filter by plate code (e.g. 01, 34)")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between API requests in seconds")
    args = parser.parse_args()

    seed: list[dict[str, Any]] = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    existing_map: dict[str, dict[str, Any]] = {}
    if args.resume and DATASET_PATH.exists():
        for item in json.loads(DATASET_PATH.read_text(encoding="utf-8")):
            img_file = ROOT / item["imagePath"]
            if img_file.exists():
                existing_map[item["id"]] = item

    targets = [
        item for item in seed
        if (not args.category or item["category"] == args.category)
        and (not args.plate or item["plate"] == args.plate)
    ]
    if args.limit > 0:
        targets = targets[: args.limit]

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: dict[str, dict[str, Any]] = dict(existing_map)
    missing: list[dict[str, Any]] = []

    processed = 0
    for idx, item in enumerate(targets, start=1):
        item_id = item["id"]
        if item_id in results:
            continue

        print(f"[{idx}/{len(targets)}] {item['city']} ({item['category']}): {item['name']} ...")
        candidate = find_best_image(session, item["search_queries"], args.delay)
        if not candidate:
            print(f"    [MISS] No licensed image found for {item_id}")
            missing.append(item)
            continue

        rel_path = f"images/{item['category']}/{item_id}.webp"
        out_path = ROOT / rel_path
        try:
            w, h = download_and_save_webp(session, candidate["download_url"], out_path)
        except Exception as exc:
            print(f"    [ERR] Download failed for {item_id}: {exc}")
            missing.append(item)
            continue

        attribution = f"Fotoğraf: {candidate['author']} ({candidate['license']})"
        results[item_id] = {
            "id": item_id,
            "plate": item["plate"],
            "city": item["city"],
            "region": item["region"],
            "category": item["category"],
            "name": item["name"],
            "hint": item["hint"],
            "imagePath": rel_path,
            "width": w,
            "height": h,
            "author": candidate["author"],
            "license": candidate["license"],
            "attribution": attribution,
            "sourceUrl": candidate["source_url"],
        }
        print(f"    [OK] {w}x{h} | {candidate['license']} | {candidate['author']}")
        processed += 1

        if processed % 10 == 0:
            save_outputs(list(results.values()), missing)
        time.sleep(args.delay)

    save_outputs(list(results.values()), missing)
    print(f"\nDone! Saved {len(results)} items to {DATASET_PATH}, {len(missing)} missing.")


if __name__ == "__main__":
    main()
