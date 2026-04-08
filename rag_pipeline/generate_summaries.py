import pandas as pd
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


def generate_occupancy_summaries(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            brand,
            region,
            itinerary_name,
            sail_year,
            sail_quarter,
            SUM(total_bookings)                    as total_bookings,
            SUM(confirmed_bookings)                as confirmed_bookings,
            SUM(cancelled_bookings)                as cancelled_bookings,
            ROUND(AVG(occupancy_rate_pct), 2)      as avg_occupancy_pct,
            ROUND(AVG(cancellation_rate_pct), 2)   as avg_cancellation_pct,
            ROUND(AVG(avg_booking_window_days), 0) as avg_booking_window,
            ROUND(SUM(total_revenue_usd), 2)       as total_revenue
        FROM MARTS.MART_OCCUPANCY
        GROUP BY 1,2,3,4,5
        ORDER BY 1,2,4,5
    """)
    columns = [col[0].lower() for col in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=columns)

    df['sail_year']    = pd.to_datetime(df['sail_year']).dt.year
    df['sail_quarter'] = pd.to_datetime(df['sail_quarter']).dt.quarter

    documents = []
    for _, row in df.iterrows():
        quarter_name = f"Q{int(row['sail_quarter'])} {int(row['sail_year'])}"
        text = (
            f"{row['brand']} brand {row['itinerary_name']} itinerary "
            f"({row['region']} region) in {quarter_name}: "
            f"Total bookings were {int(row['total_bookings'])} with "
            f"{int(row['confirmed_bookings'])} confirmed and "
            f"{int(row['cancelled_bookings'])} cancelled. "
            f"Occupancy rate was {row['avg_occupancy_pct']}%. "
            f"Cancellation rate by region for {row['region']} was {row['avg_cancellation_pct']}%. "
            f"Average booking window was {int(row['avg_booking_window'])} days. "
            f"Total revenue was ${row['total_revenue']:,.2f}."
        )
        documents.append({
            "text": text,
            "metadata": {
                "type":      "occupancy",
                "brand":     row['brand'],
                "region":    row['region'],
                "itinerary": row['itinerary_name'],
                "year":      int(row['sail_year']),
                "quarter":   int(row['sail_quarter']),
            }
        })
    return documents


def generate_revenue_summaries(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            brand,
            region,
            cabin_category,
            YEAR(sail_date)                        as sail_year,
            QUARTER(sail_date)                     as sail_quarter,
            COUNT(*)                               as total_bookings,
            ROUND(AVG(cabin_price_usd), 2)         as avg_cabin_price,
            ROUND(AVG(total_revenue_usd), 2)       as avg_revenue,
            ROUND(AVG(total_onboard_spend_usd), 2) as avg_onboard_spend,
            ROUND(AVG(total_guest_value_usd), 2)   as avg_guest_value,
            ROUND(AVG(revenue_per_night_usd), 2)   as avg_rev_per_night
        FROM MARTS.MART_REVENUE
        WHERE NOT is_cancelled
        GROUP BY 1,2,3,4,5
        ORDER BY 1,2,3,4,5
    """)
    columns = [col[0].lower() for col in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=columns)

    documents = []
    for _, row in df.iterrows():
        quarter_name = f"Q{int(row['sail_quarter'])} {int(row['sail_year'])}"
        text = (
            f"{row['brand']} brand {row['cabin_category']} cabins "
            f"in {row['region']} region during {quarter_name}: "
            f"Average cabin price was ${row['avg_cabin_price']:,.2f}. "
            f"Average total revenue per booking was ${row['avg_revenue']:,.2f}. "
            f"Average onboard spend was ${row['avg_onboard_spend']:,.2f}. "
            f"Average total guest value was ${row['avg_guest_value']:,.2f}. "
            f"Revenue per night averaged ${row['avg_rev_per_night']:,.2f}. "
            f"Based on {int(row['total_bookings'])} confirmed bookings."
        )
        documents.append({
            "text": text,
            "metadata": {
                "type":    "revenue",
                "brand":   row['brand'],
                "region":  row['region'],
                "cabin":   row['cabin_category'],
                "year":    int(row['sail_year']),
                "quarter": int(row['sail_quarter']),
            }
        })
    return documents


def generate_pricing_summaries(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            brand,
            region,
            cabin_category,
            price_position,
            YEAR(sail_date)                     as sail_year,
            QUARTER(sail_date)                  as sail_quarter,
            COUNT(*)                            as records,
            ROUND(AVG(listed_price_usd), 2)     as avg_listed_price,
            ROUND(AVG(avg_booked_price_usd), 2) as avg_booked_price,
            ROUND(AVG(price_variance_pct), 2)   as avg_price_variance_pct
        FROM MARTS.MART_PRICING_SUMMARY
        WHERE avg_booked_price_usd IS NOT NULL
        AND price_variance_pct IS NOT NULL
        GROUP BY 1,2,3,4,5,6
        ORDER BY 1,2,3,5,6
    """)
    columns = [col[0].lower() for col in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=columns)

    documents = []
    for _, row in df.iterrows():
        quarter_name = f"Q{int(row['sail_quarter'])} {int(row['sail_year'])}"
        text = (
            f"{row['brand']} brand {row['cabin_category']} cabins "
            f"in {row['region']} during {quarter_name} were priced "
            f"{row['price_position']}. "
            f"Average listed price was ${row['avg_listed_price']:,.2f} vs "
            f"average booked price of ${row['avg_booked_price']:,.2f}. "
            f"Price variance was {row['avg_price_variance_pct']}%."
        )
        documents.append({
            "text": text,
            "metadata": {
                "type":     "pricing",
                "brand":    row['brand'],
                "region":   row['region'],
                "cabin":    row['cabin_category'],
                "position": row['price_position'],
                "year":     int(row['sail_year']),
                "quarter":  int(row['sail_quarter']),
            }
        })
    return documents


def generate_aggregate_summaries(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            region,
            brand,
            ROUND(AVG(occupancy_rate_pct), 2)    as avg_occupancy_pct,
            ROUND(AVG(cancellation_rate_pct), 2) as avg_cancellation_pct,
            ROUND(SUM(total_revenue_usd), 2)     as total_revenue,
            SUM(total_bookings)                  as total_bookings,
            ROUND(AVG(avg_booking_window_days), 0) as avg_booking_window
        FROM MARTS.MART_OCCUPANCY
        GROUP BY 1,2
        ORDER BY avg_cancellation_pct DESC
    """)
    columns = [col[0].lower() for col in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=columns)

    documents = []

    # one cross-region summary per brand
    for brand in df['brand'].unique():
        bdf = df[df['brand'] == brand].sort_values(
            'avg_cancellation_pct', ascending=False
        )
        lines = []
        for _, row in bdf.iterrows():
            lines.append(
                f"{row['region']}: cancellation rate {row['avg_cancellation_pct']}%, "
                f"occupancy {row['avg_occupancy_pct']}%, "
                f"avg booking window {int(row['avg_booking_window'])} days, "
                f"total revenue ${row['total_revenue']:,.2f}"
            )
        text = (
            f"{brand} brand cancellation rate and occupancy rate comparison across all regions: "
            + " | ".join(lines)
        )
        documents.append({
            "text": text,
            "metadata": {
                "type":  "aggregate",
                "brand": brand,
            }
        })

    # one single cross-brand cross-region summary
    overall = df.groupby('region').agg(
        avg_cancellation=('avg_cancellation_pct', 'mean'),
        avg_occupancy=('avg_occupancy_pct', 'mean'),
        total_revenue=('total_revenue', 'sum'),
    ).round(2).sort_values('avg_cancellation', ascending=False).reset_index()

    lines = []
    for _, row in overall.iterrows():
        lines.append(
            f"{row['region']}: avg cancellation rate {row['avg_cancellation']}%, "
            f"avg occupancy {row['avg_occupancy']}%, "
            f"total revenue ${row['total_revenue']:,.2f}"
        )
    text = (
        "Overall cancellation rate by region across all brands (ranked highest to lowest): "
        + " | ".join(lines)
    )
    documents.append({
        "text": text,
        "metadata": {"type": "aggregate", "brand": "all"},
    })

    return documents


def generate_all_summaries():
    print("Connecting to Snowflake...")
    conn = get_snowflake_connection()

    print("Generating occupancy summaries...")
    occ_docs = generate_occupancy_summaries(conn)
    print(f"  {len(occ_docs)} occupancy documents")

    print("Generating revenue summaries...")
    rev_docs = generate_revenue_summaries(conn)
    print(f"  {len(rev_docs)} revenue documents")

    print("Generating pricing summaries...")
    price_docs = generate_pricing_summaries(conn)
    print(f"  {len(price_docs)} pricing documents")

    print("Generating aggregate summaries...")
    agg_docs = generate_aggregate_summaries(conn)
    print(f"  {len(agg_docs)} aggregate documents")

    conn.close()

    all_docs = occ_docs + rev_docs + price_docs + agg_docs
    print(f"\nTotal documents generated: {len(all_docs)}")
    return all_docs

if __name__ == "__main__":
    docs = generate_all_summaries()
    print("\nSample document:")
    print(docs[0]['text'])