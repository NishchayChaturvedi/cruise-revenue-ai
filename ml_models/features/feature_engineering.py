import pandas as pd
import numpy as np
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os
from dotenv import load_dotenv

load_dotenv()

def get_snowflake_connection():
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
    return snowflake.connector.connect(
        user        = os.getenv("SNOWFLAKE_USER"),
        account     = os.getenv("SNOWFLAKE_ACCOUNT"),
        private_key = private_key_bytes,
        warehouse   = "CRUISE_WH",
        database    = "CRUISE_REVENUE_AI",
        schema      = "MARTS",
        role        = "SYSADMIN"
    )


def load_features():
    print("Connecting to Snowflake...")
    conn = get_snowflake_connection()

    print("Loading mart_revenue...")
    revenue_df = pd.read_sql("""
        SELECT
            booking_id,
            guest_id,
            brand,
            ship_name,
            itinerary_name,
            region,
            nights,
            cabin_category,
            num_guests,
            booking_date,
            sail_date,
            booking_window_days,
            cabin_price_usd,
            total_revenue_usd,
            total_onboard_spend_usd,
            total_guest_value_usd,
            booking_channel,
            is_cancelled,
            loyalty_tier
        FROM MARTS.MART_REVENUE
    """, conn)

    print("Loading mart_guest_ltv...")
    ltv_df = pd.read_sql("""
        SELECT
            guest_id,
            total_bookings,
            completed_voyages,
            customer_tenure_days,
            total_lifetime_value,
            avg_cabin_price,
            ltv_segment
        FROM MARTS.MART_GUEST_LTV
    """, conn)

    conn.close()
    print(f"Loaded {len(revenue_df):,} booking records")

    # normalize column names to lowercase before merge
    revenue_df.columns = [c.lower() for c in revenue_df.columns]
    ltv_df.columns     = [c.lower() for c in ltv_df.columns]

    # ── Merge guest LTV into bookings ────────────────────────────────────────
    df = revenue_df.merge(ltv_df, on='guest_id', how='left')

    # ── Date features ────────────────────────────────────────────────────────
    df['sail_date']    = pd.to_datetime(df['SAIL_DATE']    if 'SAIL_DATE'    in df.columns else df['sail_date'])
    df['booking_date'] = pd.to_datetime(df['BOOKING_DATE'] if 'BOOKING_DATE' in df.columns else df['booking_date'])


    df['sail_month']      = df['sail_date'].dt.month
    df['sail_quarter']    = df['sail_date'].dt.quarter
    df['sail_year']       = df['sail_date'].dt.year
    df['sail_dayofweek']  = df['sail_date'].dt.dayofweek
    df['is_peak_season']  = df['sail_month'].isin([6, 7, 8, 12]).astype(int)
    df['is_weekend_sail'] = df['sail_dayofweek'].isin([4, 5]).astype(int)

    # ── Encode categoricals ──────────────────────────────────────────────────
    brand_map    = {'Norwegian': 0, 'Oceania': 1, 'Regent': 2}
    channel_map  = {'Direct Web': 0, 'Travel Agent': 1, 'OTA': 2, 'Group': 3, 'Loyalty': 4}
    loyalty_map  = {'None': 0, 'Latitudes': 1, 'Gold': 2, 'Platinum': 3, 'Ambassador': 4}
    region_map   = {'Caribbean': 0, 'Alaska': 1, 'Mediterranean': 2, 'Europe': 3,
                    'Americas': 4, 'Bermuda': 5, 'Hawaii': 6, 'Asia': 7}

    df['brand_enc']    = df['brand'].map(brand_map).fillna(0)
    df['channel_enc']  = df['booking_channel'].map(channel_map).fillna(0)
    df['loyalty_enc']  = df['loyalty_tier'].map(loyalty_map).fillna(0)
    df['region_enc']   = df['region'].map(region_map).fillna(0)

    # cabin category encoding
    all_cabins = df['cabin_category'].unique()
    cabin_map  = {c: i for i, c in enumerate(sorted(all_cabins))}
    df['cabin_enc'] = df['cabin_category'].map(cabin_map).fillna(0)

    print(f"Feature engineering complete — {len(df):,} rows, {len(df.columns)} columns")
    return df


def get_feature_columns():
    return [
        'brand_enc', 'region_enc', 'cabin_enc', 'channel_enc', 'loyalty_enc',
        'nights', 'num_guests', 'booking_window_days', 'cabin_price_usd',
        'sail_month', 'sail_quarter', 'sail_year', 'is_peak_season',
        'is_weekend_sail', 'total_bookings', 'completed_voyages',
        'customer_tenure_days', 'avg_cabin_price'
    ]