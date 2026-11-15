import getpass
import os
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

password = getpass.getpass("Enter your PostgreSQL password: ")

try:
    with psycopg.connect(
        host="localhost",
        port=5432,
        dbname="vehicle_parts",
        user="postgres",
        password=password,
        connect_timeout=10,
    ) as connection:
        result = connection.execute(
            "SELECT current_database(), version();"
        ).fetchone()

        print("Connected to database:", result[0])
        print("PostgreSQL version:", result[1])

except Exception as error:
    print("Connection failed:")
    print(error)