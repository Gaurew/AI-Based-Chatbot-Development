import argparse
import asyncio
import json
from pathlib import Path
from typing import List, Tuple

from playwright.async_api import async_playwright

from app.config import get_settings
from app.models.schema import JobRecord
from .categories import CATEGORY_URLS
from .fetch import collect_detail_urls_for_category
from .parse import parse_job_detail


DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_detail(page, detail_url: str) -> str:
    await page.goto(detail_url, wait_until="domcontentloaded")
    return await page.content()


async def scrape_category(category: str) -> List[JobRecord]:
    settings = get_settings()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=settings.user_agent)
        page = await context.new_page()

        print(f"[scrape] Navigating category='{category}' ...")
        discovered: List[Tuple[str, str]] = await collect_detail_urls_for_category(page, category)
        print(f"[scrape] Discovered {len(discovered)} detail URLs for category='{category}'")

        records: List[JobRecord] = []
        for idx, (detail_url, cat) in enumerate(discovered, start=1):
            print(f"[scrape] ({idx}/{len(discovered)}) Fetching detail: {detail_url}")
            html = await fetch_detail(page, detail_url)
            record_dict = parse_job_detail(html, detail_url, cat)
            try:
                record = JobRecord(**record_dict)
                records.append(record)
            except Exception as e:
                print(f"[scrape] Parse validation failed for {detail_url}: {e}")

        await context.close()
        await browser.close()
        return records


def write_outputs(records: List[JobRecord]):
    # JSONL
    jsonl_path = PROC_DIR / "jobs.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.model_dump_json())
            f.write("\n")

    # CSV (minimal)
    import csv

    csv_path = PROC_DIR / "jobs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "category",
                "postTitle",
                "organizationName",
                "numVacancies",
                "salary",
                "ageRequirement",
                "experienceRequired",
                "qualification",
                "location",
                "lastDate",
                "postedDate",
                "sourceUrl",
            ],
        )
        writer.writeheader()
        for r in records:
            row = r.model_dump()
            row.pop("tags", None)
            writer.writerow(row)


async def main_async(args):
    targets = []
    if args.all:
        targets = list(CATEGORY_URLS.keys())
    elif args.category:
        targets = [args.category.lower()]
    else:
        raise SystemExit("Provide --all or --category <name>")

    all_records: List[JobRecord] = []
    for cat in targets:
        cat_records = await scrape_category(cat)
        print(f"[scrape] Parsed {len(cat_records)} records for category='{cat}'")
        all_records.extend(cat_records)

    # Deduplicate by sourceUrl
    seen = set()
    unique: List[JobRecord] = []
    for r in all_records:
        if r.sourceUrl not in seen:
            unique.append(r)
            seen.add(r.sourceUrl)

    write_outputs(unique)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, help="engineering|science|commerce|education")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()


