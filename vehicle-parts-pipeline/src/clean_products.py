import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

project_folder = Path(__file__).resolve().parent.parent
input_file = (
    project_folder / "data" / "processed" / "partsforcars_products.csv"
)
output_file = (
    project_folder / "data" / "processed" / "partsforcars_products_clean.csv"
)

columns = [
    "product_name",
    "part_number",
    "price_vat_included",
    "price_vat_excluded",
    "availability",
    "category",
    "product_url",
]


def clean_text(value):
    """Trim a value and replace repeated whitespace with single spaces."""
    return " ".join((value or "").split())


def clean_price(value):
    """Convert a euro price such as '€19.76' to '19.76'."""
    value = clean_text(value)

    if not value:
        return ""

    value = re.sub(r"[€\s]", "", value)

    # Handle prices that use a comma as the decimal separator.
    if "," in value and "." not in value:
        value = value.replace(",", ".")

    # Remove thousands separators when both separators are present.
    elif "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")

    try:
        return format(Decimal(value), ".2f")
    except InvalidOperation:
        # Keep the original cleaned text if it is not a recognisable price.
        return value


def clean_availability(value):
    """Standardise spacing and capitalisation without changing the message."""
    value = clean_text(value)

    if not value:
        return ""

    return value[0].upper() + value[1:].lower()


if not input_file.exists():
    raise FileNotFoundError(f"Input CSV not found: {input_file}")

with input_file.open("r", newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    missing_columns = set(columns) - set(reader.fieldnames or [])
    if missing_columns:
        raise ValueError(
            f"Input CSV is missing columns: {sorted(missing_columns)}"
        )

    rows = list(reader)

cleaned_rows = []
seen_urls = set()
duplicate_count = 0

for row in rows:
    cleaned = {
        "product_name": clean_text(row.get("product_name")),
        "part_number": clean_text(row.get("part_number")),
        "price_vat_included": clean_price(
            row.get("price_vat_included")
        ),
        "price_vat_excluded": clean_price(
            row.get("price_vat_excluded")
        ),
        "availability": clean_availability(row.get("availability")),
        "category": clean_text(row.get("category")),
        "product_url": clean_text(row.get("product_url")),
    }

    url = cleaned["product_url"]
    if url and url in seen_urls:
        duplicate_count += 1
        continue

    if url:
        seen_urls.add(url)

    cleaned_rows.append(cleaned)

with output_file.open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(cleaned_rows)

print("Input rows:", len(rows))
print("Cleaned rows:", len(cleaned_rows))
print("Duplicate rows removed:", duplicate_count)
print("Rows with missing product name:", sum(
    not row["product_name"] for row in cleaned_rows
))
print("Rows with missing part number:", sum(
    not row["part_number"] for row in cleaned_rows
))
print("Rows with missing VAT-inclusive price:", sum(
    not row["price_vat_included"] for row in cleaned_rows
))
print("Rows with missing VAT-exclusive price:", sum(
    not row["price_vat_excluded"] for row in cleaned_rows
))
print("Rows with missing availability:", sum(
    not row["availability"] for row in cleaned_rows
))
print("Cleaned CSV saved to:", output_file)