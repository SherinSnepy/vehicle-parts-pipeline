import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    project_folder = Path(__file__).resolve().parent.parent
    raw_folder = project_folder / "data" / "raw"
    raw_folder.mkdir(parents=True, exist_ok=True)

    url = "https://partsforcars.ie/oil-filters"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            channel="msedge",
            headless=False
        )

        page = await browser.new_page()
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        print("Status:", response.status if response else "No response")
        print("Page title:", await page.title())
        print("Final URL:", page.url)

        product_count = await page.locator(
            "a.incart_listing_title_anchor"
        ).count()
        print("Product links found:", product_count)

        html = await page.content()
        output_file = raw_folder / "oil_filters.html"
        output_file.write_text(html, encoding="utf-8")

        print("Saved HTML to:", output_file)

        await browser.close()


asyncio.run(main())