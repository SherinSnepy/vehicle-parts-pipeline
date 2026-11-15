import csv
import getpass
import os
from decimal import Decimal
from pathlib import Path

# Help Windows find PostgreSQL's client library.
postgres_bin = Path(r"C:\Program Files\PostgreSQL\18\bin")
dll_directory = None

if postgres_bin.exists():
    os.environ["PATH"] = (
        str(postgres_bin) + os.pathsep + os.environ.get("PATH", "")
    )
    dll_directory = os.add_dll_directory(str(postgres_bin))

import psycopg


project_folder = Path(__file__).resolve().parent.parent
csv_file = (
    project_folder
    / "data"
    / "processed"
    / "partsforcars_products_clean.csv"
)

if not csv_file.exists():
    raise FileNotFoundError(f"Cleaned CSV not found: {csv_file}")


def price_or_none(value):
    value = (value or "").strip()
    return Decimal(value) if value else None


with csv_file.open("r", newline="", encoding="utf-8-sig") as file:
    rows = list(csv.DictReader(file))

password = getpass.getpass("Enter your PostgreSQL password: ")

with psycopg.connect(
    host="localhost",
    port=5432,
    dbname="vehicle_parts",
    user="postgres",
    password=password,
) as connection:
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id BIGSERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                part_number TEXT,
                price_vat_included NUMERIC(10, 2),
                price_vat_excluded NUMERIC(10, 2),
                availability TEXT,
                category TEXT NOT NULL,
                product_url TEXT NOT NULL UNIQUE
            )
        """)

        # Replace this project's table contents with the latest CSV.
        cursor.execute("DELETE FROM products")

        cursor.executemany(
            """
            INSERT INTO products (
                product_name,
                part_number,
                price_vat_included,
                price_vat_excluded,
                availability,
                category,
                product_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    row["product_name"].strip(),
                    row["part_number"].strip() or None,
                    price_or_none(row["price_vat_included"]),
                    price_or_none(row["price_vat_excluded"]),
                    row["availability"].strip() or None,
                    row["category"].strip(),
                    row["product_url"].strip(),
                )
                for row in rows
            ],
        )

        cursor.execute("SELECT COUNT(*) FROM products")
        database_count = cursor.fetchone()[0]

        print("CSV rows:", len(rows))
        print("Rows now in PostgreSQL:", database_count)
        print("Database: vehicle_parts")
        print("Table: products")