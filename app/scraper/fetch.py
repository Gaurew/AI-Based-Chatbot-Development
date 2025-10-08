import asyncio
import random
from typing import List, Tuple
import re
from playwright.async_api import async_playwright, Page
from .categories import CATEGORY_URLS


CARD_SELECTOR = "div:has-text('Unlock Now') >> xpath=ancestor::div[contains(@class,'card')][1]"
DETAIL_ANCHOR_SELECTOR = "a[href*='/jobdetails/']"


async def _human_delay(min_ms: int = 500, max_ms: int = 1500):
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def collect_detail_urls_for_category(page: Page, category: str) -> List[Tuple[str, str]]:
    url = CATEGORY_URLS[category]
    await page.goto(url, wait_until="domcontentloaded")

    # Infinite scroll/lazy load with safety cap
    last_height = None
    max_scrolls = 10
    for _ in range(max_scrolls):
        height = await page.evaluate("document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await _human_delay()
    # small settle delay
    await _human_delay()

    # Collect detail URLs from anchors if present
    detail_urls: List[Tuple[str, str]] = []
    anchors = await page.query_selector_all(DETAIL_ANCHOR_SELECTOR)
    for a in anchors:
        href = await a.get_attribute("href")
        if href and "/jobdetails/" in href:
            detail_urls.append((href, category))

    # Fallback 1: regex scan all anchors on page for jobdetails links
    if not detail_urls:
        hrefs = await page.eval_on_selector_all(
            "a",
            "(nodes) => nodes.map(n => n.getAttribute('href') || '')",
        )
        for href in hrefs:
            if isinstance(href, str) and re.search(r"/jobdetails/\d+", href):
                detail_urls.append((href, category))

    # Fallback 2: regex scan full HTML for jobdetails links
    if not detail_urls:
        html = await page.content()
        for m in re.findall(r"/jobdetails/(\d+)", html):
            detail_urls.append((f"/jobdetails/{m}", category))

    # Fallback: click cards to capture navigation URL when anchors aren’t available
    if not detail_urls:
        cards = await page.query_selector_all("a[href*='/jobdetails/'], div.card, div:has(a)")
        seen = set()
        for card in cards:
            try:
                async with page.expect_navigation(wait_until="load", timeout=15000):
                    await card.click(force=True)
                dest = page.url
                if "/jobdetails/" in dest and dest not in seen:
                    detail_urls.append((dest, category))
                    seen.add(dest)
                await page.go_back(wait_until="domcontentloaded")
                await _human_delay()
            except Exception:
                # Skip problematic cards
                continue

    # Deduplicate and absolutize
    dedup = []
    seen = set()
    for href, cat in detail_urls:
        if href.startswith("/"):
            href = f"https://www.jobyaari.com{href}"
        if href not in seen:
            dedup.append((href, cat))
            seen.add(href)
    return dedup


