import asyncio
import csv
import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


CATEGORY_URLS = [
    "https://partsforcars.ie/oil-filters",
    "https://partsforcars.ie/air-filters",
    "https://partsforcars.ie/fuel-filters",
    "https://partsforcars.ie/cabin-filters",
    "https://partsforcars.ie/batteries-2",
    "https://partsforcars.ie/wiper-blades",
    "https://partsforcars.ie/headlight-bulbs",
    "https://partsforcars.ie/spark-plugs",
    "https://partsforcars.ie/glow-plugs",
    "https://partsforcars.ie/transmission-filters-2",    
    "https://partsforcars.ie/brake-pads",
    "https://partsforcars.ie/brake-discs",
    "https://partsforcars.ie/brake-hoses",
    "https://partsforcars.ie/abs-sensors",
    "https://partsforcars.ie/brake-shoes",
    "https://partsforcars.ie/brake-cables",
    "https://partsforcars.ie/brake-pad-fitting-kits",
    "https://partsforcars.ie/brake-fluid-4",
    "https://partsforcars.ie/brake-shoe-fitting-kits",
    "https://partsforcars.ie/brake-drums",
    "https://partsforcars.ie/brake-calipers",
    "https://partsforcars.ie/brake-light-switches",
    "https://partsforcars.ie/brake-master-cylinders",
    "https://partsforcars.ie/brake-wear-sensors",
    "https://partsforcars.ie/brake-wheel-cylinders",    
    "https://partsforcars.ie/wing-mirrors",
    "https://partsforcars.ie/window-regulators",
    "https://partsforcars.ie/boot-bonnet-struts",
    "https://partsforcars.ie/body-panels",
    "https://partsforcars.ie/bumpers",
    "https://partsforcars.ie/shock-absorbers",
    "https://partsforcars.ie/control-arms-links",
    "https://partsforcars.ie/coil-springs",
    "https://partsforcars.ie/ball-joints",
    "https://partsforcars.ie/mounts",
    "https://partsforcars.ie/tie-rods",
    "https://partsforcars.ie/bushes",
    "https://partsforcars.ie/subframe-bushes",
]

project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "processed"
output_folder.mkdir(parents=True, exist_ok=True)
csv_file = output_folder / "partsforcars_products.csv"


def clean_text(element):
    if element is None:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def get_category(url):
    slug = urlparse(url).path.strip("/").split("/")[-1]
    return slug.replace("-", " ").title()



def specification_part_number(specification_block):
    if not specification_block:
        return ""

    labels = specification_block.select(
        ".incart_summary_specification_label_cell"
    )
    values = specification_block.select(
        ".incart_summary_specification_value_cell"
    )

    for label, value in zip(labels, values):
        label_text = clean_text(label).lower()

        if any(term in label_text for term in (
            "part number",
            "article number",
            "item number",
            "manufacturer number",
        )):
            return clean_text(value)

    return ""


def split_title_and_part_number(title, spec_part_number=""):
    # Use a part number from the specifications, if available.
    if spec_part_number:
        product_name = title.replace(spec_part_number, "").strip()
        return product_name, spec_part_number

    # Otherwise, treat a code-like final word as the part number.
    match = re.search(
        r"\s+([A-Z0-9][A-Z0-9./_-]*\d[A-Z0-9./_-]*)$",
        title,
        re.IGNORECASE,
    )

    if match:
        part_number = match.group(1).strip()
        product_name = title[:match.start()].strip()
        return product_name, part_number

    # No clear part number was found: keep the full title as the name.
    return title, ""


def extract_prices(price_block):
    if not price_block:
        return "", ""

    price_text = clean_text(price_block)
    amounts = re.findall(r"€\s*\d+(?:[.,]\d{2})", price_text)

    vat_included = amounts[0] if len(amounts) >= 1 else ""
    vat_excluded = amounts[1] if len(amounts) >= 2 else ""

    return vat_included, vat_excluded


async def main():
    products = []
    seen_urls = set()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            channel="msedge",
            headless=False,
        )
        page = await browser.new_page()

        for category_url in CATEGORY_URLS:
            try:
                response = await page.goto(
                    category_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                await page.wait_for_timeout(4000)

                # Scroll to help load product content that appears further down.
                for _ in range(3):
                    await page.mouse.wheel(0, 1000)
                    await page.wait_for_timeout(500)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                links = soup.select("a.incart_listing_title_anchor")
                prices = soup.select(".incart_summary_price")
                spec_blocks = soup.select(
                    ".incart_summary_specification_modal_content"
                )

                stock_labels = []

                for text in soup.find_all(string=True):
                    value = " ".join(str(text).split())
                
                    if "in stock" in value.lower():
                        stock_labels.append(value)

                status = response.status if response else "No response"
                print(
                    f"{category_url} | Status: {status} "
                    f"| Products found: {len(links)}"
                )

                for index, link in enumerate(links):
                    title = clean_text(link)
                    product_url = link.get("href", "").strip()

                    # Avoid saving the same product more than once.
                    if not product_url or product_url in seen_urls:
                        continue
                    seen_urls.add(product_url)

                    spec_block = (
                        spec_blocks[index]
                        if index < len(spec_blocks)
                        else None
                    )

                    spec_part = specification_part_number(spec_block)
                    product_name, part_number = split_title_and_part_number(
                        title, spec_part
                    )

                    price_included, price_excluded = (
                        extract_prices(prices[index])
                        if index < len(prices)
                        else ("", "")
                    )

                    availability = (
                        stock_labels[index]
                        if index < len(stock_labels)
                        else ""
                    )

                    

                    products.append({
                        "product_name": product_name,
                        "part_number": part_number,
                        "price_vat_included": price_included,
                        "price_vat_excluded": price_excluded,
                        "availability": availability,
                        "category": get_category(category_url),
                        "product_url": product_url,
                    })

            except Exception as error:
                print(f"Error on {category_url}: {error}")

        await browser.close()

    columns = [
        "product_name",
        "part_number",
        "price_vat_included",
        "price_vat_excluded",
        "availability",
        "category",
        "product_url",
    ]

    with csv_file.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(products)

    print(f"\nTotal unique products saved: {len(products)}")
    print(f"CSV saved to: {csv_file}")


asyncio.run(main())