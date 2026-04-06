import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import os

fake = Faker()
np.random.seed(42)
random.seed(42)

# ── Brand & ship configuration ───────────────────────────────────────────────
BRANDS = {
    "Norwegian": {
        "ships": ["Norwegian Encore", "Norwegian Bliss", "Norwegian Joy",
                  "Norwegian Escape", "Norwegian Getaway"],
        "cabin_categories": ["Inside", "Oceanview", "Balcony", "Mini-Suite", "Haven Suite"],
        "base_price_range": (599, 4999),
        "avg_occupancy": 0.88,
    },
    "Oceania": {
        "ships": ["Marina", "Riviera", "Vista", "Allura"],
        "cabin_categories": ["Inside", "Oceanview", "Veranda", "Concierge", "Penthouse"],
        "base_price_range": (1999, 12999),
        "avg_occupancy": 0.82,
    },
    "Regent": {
        "ships": ["Seven Seas Explorer", "Seven Seas Splendor",
                  "Seven Seas Grandeur", "Seven Seas Mariner"],
        "cabin_categories": ["Deluxe Suite", "Superior Suite", "Penthouse Suite",
                             "Grand Suite", "Master Suite"],
        "base_price_range": (4999, 29999),
        "avg_occupancy": 0.76,
    },
}

ITINERARIES = [
    {"name": "Caribbean Classic",    "region": "Caribbean",     "nights": 7,  "ports": ["Miami", "Nassau", "CocoCay", "Miami"]},
    {"name": "Alaska Explorer",      "region": "Alaska",        "nights": 7,  "ports": ["Seattle", "Juneau", "Skagway", "Ketchikan", "Seattle"]},
    {"name": "Mediterranean Dreams", "region": "Mediterranean", "nights": 10, "ports": ["Barcelona", "Rome", "Santorini", "Athens", "Barcelona"]},
    {"name": "Norwegian Fjords",     "region": "Europe",        "nights": 9,  "ports": ["Copenhagen", "Bergen", "Geiranger", "Flam", "Copenhagen"]},
    {"name": "Panama Canal",         "region": "Americas",      "nights": 14, "ports": ["Miami", "Cartagena", "Panama City", "Puerto Vallarta", "Los Angeles"]},
    {"name": "Bermuda Getaway",      "region": "Bermuda",       "nights": 5,  "ports": ["New York", "Hamilton", "New York"]},
    {"name": "Hawaii Aloha",         "region": "Hawaii",        "nights": 12, "ports": ["Honolulu", "Maui", "Kauai", "Big Island", "Honolulu"]},
    {"name": "Asia Discovery",       "region": "Asia",          "nights": 14, "ports": ["Singapore", "Bangkok", "Ho Chi Minh", "Hong Kong", "Singapore"]},
]

BOOKING_CHANNELS  = ["Direct Web", "Travel Agent", "OTA", "Group", "Loyalty"]
CANCELLATION_REASONS = ["Personal", "Medical", "Price", "Weather", "Work", None]


# ── Helpers ──────────────────────────────────────────────────────────────────
def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def booking_window_days(brand):
    if brand == "Regent":
        return random.randint(60, 540)
    elif brand == "Oceania":
        return random.randint(30, 365)
    else:
        return random.randint(7, 270)


def price_with_seasonality(base_price, sail_date, region, booking_window):
    month = sail_date.month
    seasonal_factor = 1.0
    if region == "Caribbean"     and month in [12, 1, 2, 3]: seasonal_factor = 1.25
    elif region == "Alaska"      and month in [6, 7, 8]:     seasonal_factor = 1.30
    elif region == "Mediterranean" and month in [7, 8]:      seasonal_factor = 1.35
    elif region == "Europe"      and month in [6, 7, 8]:     seasonal_factor = 1.20

    early_bird = 0.85 if booking_window > 180 else 0.92 if booking_window > 90 else 1.0
    return round(base_price * seasonal_factor * early_bird * random.uniform(0.95, 1.05), 2)


# ── Table 1: Bookings ────────────────────────────────────────────────────────
def generate_bookings(n=50000):
    records = []
    sail_start = datetime(2022, 1, 1)
    sail_end   = datetime(2025, 12, 31)

    for i in range(n):
        brand     = random.choices(list(BRANDS.keys()), weights=[0.60, 0.25, 0.15])[0]
        config    = BRANDS[brand]
        ship      = random.choice(config["ships"])
        itinerary = random.choice(ITINERARIES)
        cabin_cat = random.choice(config["cabin_categories"])

        sail_date      = random_date(sail_start, sail_end)
        bw             = booking_window_days(brand)
        booking_date   = sail_date - timedelta(days=bw)
        guests         = random.choices([1, 2, 3, 4], weights=[0.15, 0.60, 0.15, 0.10])[0]
        base_price     = random.uniform(*config["base_price_range"])
        cabin_price    = price_with_seasonality(base_price, sail_date, itinerary["region"], bw)

        is_cancelled       = random.random() < 0.12
        cancellation_date  = None
        cancellation_reason = None
        if is_cancelled:
            days_before = random.randint(1, bw)
            cancellation_date   = sail_date - timedelta(days=days_before)
            cancellation_reason = random.choice(CANCELLATION_REASONS)

        records.append({
            "booking_id":           f"BK{i+1:07d}",
            "guest_id":             f"G{random.randint(1, 20000):07d}",
            "brand":                brand,
            "ship_name":            ship,
            "itinerary_name":       itinerary["name"],
            "region":               itinerary["region"],
            "nights":               itinerary["nights"],
            "cabin_category":       cabin_cat,
            "num_guests":           guests,
            "booking_date":         booking_date.date(),
            "sail_date":            sail_date.date(),
            "booking_window_days":  bw,
            "cabin_price_usd":      cabin_price,
            "total_revenue_usd":    round(cabin_price * guests * random.uniform(0.95, 1.10), 2),
            "booking_channel":      random.choice(BOOKING_CHANNELS),
            "is_cancelled":         is_cancelled,
            "cancellation_date":    cancellation_date.date() if cancellation_date else None,
            "cancellation_reason":  cancellation_reason,
            "loyalty_tier":         random.choices(
                                        ["None", "Latitudes", "Gold", "Platinum", "Ambassador"],
                                        weights=[0.40, 0.25, 0.18, 0.12, 0.05]
                                    )[0],
            "_fivetran_synced":     datetime.now().isoformat(),
        })

    return pd.DataFrame(records)


# ── Table 2: Guest profiles ──────────────────────────────────────────────────
def generate_guests(bookings_df):
    records = []
    for gid in bookings_df["guest_id"].unique():
        gb = bookings_df[bookings_df["guest_id"] == gid]
        records.append({
            "guest_id":         gid,
            "first_name":       fake.first_name(),
            "last_name":        fake.last_name(),
            "email":            fake.email(),
            "country":          random.choices(
                                    ["USA", "UK", "Canada", "Australia", "Germany", "France", "Other"],
                                    weights=[0.55, 0.12, 0.10, 0.07, 0.06, 0.05, 0.05]
                                )[0],
            "age_group":        random.choices(
                                    ["25-34", "35-44", "45-54", "55-64", "65+"],
                                    weights=[0.10, 0.20, 0.28, 0.25, 0.17]
                                )[0],
            "primary_brand":    gb["brand"].mode()[0],
            "total_bookings":   len(gb),
            "loyalty_tier":     gb["loyalty_tier"].iloc[-1],
            "_fivetran_synced": datetime.now().isoformat(),
        })
    return pd.DataFrame(records)


# ── Table 3: Onboard spend ───────────────────────────────────────────────────
def generate_onboard_spend(bookings_df):
    active = bookings_df[bookings_df["is_cancelled"] == False].copy()
    spend_profile = {
        "Norwegian": {"dining": (0, 300),  "spa": (0, 250),  "excursions": (0, 800),  "beverage": (0, 400), "casino": (0, 500), "retail": (0, 200)},
        "Oceania":   {"dining": (0, 150),  "spa": (0, 400),  "excursions": (0, 1200), "beverage": (0, 200), "casino": (0, 100), "retail": (0, 350)},
        "Regent":    {"dining": (0, 0),    "spa": (0, 600),  "excursions": (0, 2000), "beverage": (0, 0),   "casino": (0, 200), "retail": (0, 500)},
    }
    records = []
    for _, row in active.iterrows():
        profile = spend_profile[row["brand"]]
        spend   = {cat: round(random.uniform(*rng) * row["num_guests"], 2)
                   for cat, rng in profile.items()}
        spend["booking_id"]             = row["booking_id"]
        spend["guest_id"]               = row["guest_id"]
        spend["brand"]                  = row["brand"]
        spend["sail_date"]              = row["sail_date"]
        spend["total_onboard_spend_usd"] = round(sum(
            v for k, v in spend.items()
            if k not in ["booking_id", "guest_id", "brand", "sail_date"]
        ), 2)
        spend["_fivetran_synced"]       = datetime.now().isoformat()
        records.append(spend)
    return pd.DataFrame(records)


# ── Table 4: Pricing log ─────────────────────────────────────────────────────
def generate_pricing_log(bookings_df):
    records = []
    for itinerary in ITINERARIES:
        for brand in BRANDS:
            config = BRANDS[brand]
            sail_start = datetime(2022, 1, 1)
            sail_end   = datetime(2025, 12, 31)
            current    = sail_start
            while current <= sail_end:
                for cabin_cat in config["cabin_categories"]:
                    base   = random.uniform(*config["base_price_range"])
                    price  = price_with_seasonality(base, current, itinerary["region"], 90)
                    records.append({
                        "price_log_id":    f"PL{len(records)+1:09d}",
                        "brand":           brand,
                        "itinerary_name":  itinerary["name"],
                        "region":          itinerary["region"],
                        "cabin_category":  cabin_cat,
                        "sail_date":       current.date(),
                        "price_usd":       price,
                        "recorded_at":     datetime.now().isoformat(),
                        "_fivetran_synced": datetime.now().isoformat(),
                    })
                current += timedelta(days=7)
    return pd.DataFrame(records)


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    print("Generating bookings (50,000 records)...")
    bookings = generate_bookings(50000)
    bookings.to_csv("data/raw/bookings.csv", index=False)
    print(f"  Done — {len(bookings):,} rows")

    print("Generating guest profiles...")
    guests = generate_guests(bookings)
    guests.to_csv("data/raw/guests.csv", index=False)
    print(f"  Done — {len(guests):,} rows")

    print("Generating onboard spend...")
    spend = generate_onboard_spend(bookings)
    spend.to_csv("data/raw/onboard_spend.csv", index=False)
    print(f"  Done — {len(spend):,} rows")

    print("Generating pricing log...")
    pricing = generate_pricing_log(bookings)
    pricing.to_csv("data/raw/pricing_log.csv", index=False)
    print(f"  Done — {len(pricing):,} rows")

    print("\nAll datasets generated in data/raw/")
    print("\nSample bookings:")
    print(bookings.head(3).to_string())