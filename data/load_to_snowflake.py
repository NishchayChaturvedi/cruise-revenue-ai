import snowflake.connector
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os
from dotenv import load_dotenv

load_dotenv()

# ── Load private key ──────────────────────────────────────────────────────────
with open(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"), "rb") as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
        backend=default_backend()
    )

private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# ── Connection ────────────────────────────────────────────────────────────────
conn = snowflake.connector.connect(
    user             = os.getenv("SNOWFLAKE_USER"),
    account          = os.getenv("SNOWFLAKE_ACCOUNT"),
    private_key      = private_key_bytes,
    warehouse        = "CRUISE_WH",
    database         = "CRUISE_REVENUE_AI",
    schema           = "RAW",
    role             = "CRUISE_DEV"
)

print("Connected to Snowflake successfully")

# ── Table map ─────────────────────────────────────────────────────────────────
tables = {
    "STG_BOOKINGS":      "data/raw/bookings.csv",
    "STG_GUESTS":        "data/raw/guests.csv",
    "STG_ONBOARD_SPEND": "data/raw/onboard_spend.csv",
    "STG_PRICING_LOG":   "data/raw/pricing_log.csv",
}

# ── Load each table ───────────────────────────────────────────────────────────
for table_name, csv_path in tables.items():
    print(f"\nLoading {csv_path} → {table_name}...")

    df = pd.read_csv(csv_path)
    df.columns = [c.upper() for c in df.columns]

    success, chunks, rows, output = write_pandas(
        conn              = conn,
        df                = df,
        table_name        = table_name,
        database          = "CRUISE_REVENUE_AI",
        schema            = "RAW",
        auto_create_table = False,
        overwrite         = True,
    )

    if success:
        print(f"  Loaded {rows:,} rows into {table_name}")
    else:
        print(f"  Failed: {output}")

conn.close()
print("\nAll tables loaded. Snowflake connection closed.")