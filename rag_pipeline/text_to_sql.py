import snowflake.connector
import anthropic
import os
import re
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_conn():
    with open(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"), "rb") as f:
        pk = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )
    pk_bytes = pk.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    )
    return snowflake.connector.connect(
        user        = os.getenv("SNOWFLAKE_USER"),
        account     = os.getenv("SNOWFLAKE_ACCOUNT"),
        private_key = pk_bytes,
        warehouse   = "CRUISE_WH",
        database    = "CRUISE_REVENUE_AI",
        schema      = "MARTS",
        role        = "SYSADMIN"
    )


# ── Full schema context given to Claude ──────────────────────────────────────
SCHEMA_CONTEXT = """
You have access to a Snowflake data warehouse for Norwegian Cruise Line Holdings (NCLH).
NCLH operates three cruise brands: Norwegian (mass market), Oceania (premium), Regent (ultra-luxury).

Available tables in CRUISE_REVENUE_AI.MARTS schema:

TABLE: MART_REVENUE
One row per booking. Use for revenue, pricing, cabin, guest, and booking analysis.
Columns:
- BOOKING_ID (varchar) — unique booking identifier
- GUEST_ID (varchar) — guest identifier
- BRAND (varchar) — Norwegian, Oceania, or Regent
- SHIP_NAME (varchar) — name of the ship
- ITINERARY_NAME (varchar) — e.g. Caribbean Classic, Alaska Explorer
- REGION (varchar) — Caribbean, Alaska, Mediterranean, Europe, Americas, Bermuda, Hawaii, Asia
- NIGHTS (integer) — cruise duration
- CABIN_CATEGORY (varchar) — Inside, Oceanview, Balcony, Mini-Suite, Haven Suite (Norwegian); Inside, Oceanview, Veranda, Concierge, Penthouse (Oceania); Deluxe Suite, Superior Suite, Penthouse Suite, Grand Suite, Master Suite (Regent)
- NUM_GUESTS (integer) — number of guests in cabin
- BOOKING_DATE (date) — when booking was made
- SAIL_DATE (date) — when cruise departs
- BOOKING_WINDOW_DAYS (integer) — days between booking and sail date
- CABIN_PRICE_USD (float) — cabin price
- TOTAL_REVENUE_USD (float) — total cabin revenue
- BOOKING_CHANNEL (varchar) — Direct Web, Travel Agent, OTA, Group, Loyalty
- IS_CANCELLED (boolean) — whether booking was cancelled
- CANCELLATION_REASON (varchar) — reason if cancelled
- LOYALTY_TIER (varchar) — None, Latitudes, Gold, Platinum, Ambassador
- TOTAL_ONBOARD_SPEND_USD (float) — total onboard spend
- DINING_SPEND (float) — dining spend
- SPA_SPEND (float) — spa spend
- EXCURSIONS_SPEND (float) — excursions spend
- BEVERAGE_SPEND (float) — beverage spend
- CASINO_SPEND (float) — casino spend
- RETAIL_SPEND (float) — retail spend
- TOTAL_GUEST_VALUE_USD (float) — cabin revenue + onboard spend
- REVENUE_PER_NIGHT_USD (float) — revenue per night
- TOTAL_VALUE_PER_NIGHT_USD (float) — total value per night

TABLE: MART_OCCUPANCY
Aggregated by brand, ship, itinerary, region, sail_date. Use for occupancy, cancellation trends.
Columns:
- BRAND, SHIP_NAME, ITINERARY_NAME, REGION
- SAIL_DATE (date)
- SAIL_MONTH (integer) — 1-12
- SAIL_QUARTER (integer) — 1-4
- SAIL_YEAR (integer)
- TOTAL_BOOKINGS (integer)
- CONFIRMED_BOOKINGS (integer)
- CANCELLED_BOOKINGS (integer)
- TOTAL_GUESTS (integer)
- OCCUPANCY_RATE_PCT (float) — percentage of confirmed bookings
- CANCELLATION_RATE_PCT (float) — percentage of cancelled bookings
- AVG_BOOKING_WINDOW_DAYS (float)
- AVG_CABIN_PRICE_USD (float)
- TOTAL_REVENUE_USD (float)

TABLE: MART_GUEST_LTV
One row per guest. Use for guest lifetime value, loyalty, repeat booking analysis.
Columns:
- GUEST_ID, BRAND
- TOTAL_BOOKINGS (integer)
- COMPLETED_VOYAGES (integer)
- CANCELLED_BOOKINGS (integer)
- FIRST_BOOKING_DATE (date)
- LAST_BOOKING_DATE (date)
- CUSTOMER_TENURE_DAYS (integer)
- TOTAL_CABIN_REVENUE (float)
- AVG_CABIN_PRICE (float)
- AVG_BOOKING_WINDOW_DAYS (float)
- TOTAL_ONBOARD_SPEND (float)
- TOTAL_LIFETIME_VALUE (float)
- FIRST_NAME, LAST_NAME, COUNTRY, AGE_GROUP, LOYALTY_TIER
- LTV_SEGMENT (varchar) — Platinum, Gold, Silver, Bronze

TABLE: MART_PRICING_SUMMARY
Pricing analysis by itinerary and cabin. Use for pricing and yield questions.
Columns:
- BRAND, ITINERARY_NAME, REGION, CABIN_CATEGORY
- SAIL_DATE (date)
- SAIL_MONTH (integer)
- SAIL_YEAR (integer)
- LISTED_PRICE_USD (float)
- AVG_BOOKED_PRICE_USD (float)
- PRICE_VARIANCE_PCT (float) — positive = booked above list, negative = below
- PRICE_POSITION (varchar) — Above List, At List, Below List

IMPORTANT RULES for writing SQL:
- Always use fully qualified table names: CRUISE_REVENUE_AI.MARTS.MART_REVENUE etc.
- Use ROUND() for all float calculations
- Use WHERE NOT IS_CANCELLED for revenue analysis unless asked about cancellations
- Limit results to top 10 unless the question asks for all
- Always include BRAND in GROUP BY when comparing across brands
- For year/quarter filters use SAIL_YEAR and SAIL_QUARTER columns directly
"""


def generate_sql(question):
    """Ask Claude to write a SQL query for the question."""
    prompt = f"""{SCHEMA_CONTEXT}

Write a single Snowflake SQL query to answer this question:
"{question}"

Rules:
- Return ONLY the SQL query, nothing else
- No markdown, no backticks, no explanation
- The query must be valid Snowflake SQL
- Keep it simple and focused on answering the question directly
- Always use table aliases when joining tables to avoid ambiguous column errors
- For vague questions like "how are we doing overall" query MART_REVENUE 
  grouped by BRAND showing total revenue, total bookings, avg guest value
- For "problem areas" query MART_OCCUPANCY for low occupancy or high cancellation
- Never use SELECT * — always specify column names explicitly
- When using aggregations always qualify column names with table alias
- For trend questions use MART_OCCUPANCY table only — it has SAIL_YEAR, 
  SAIL_QUARTER, SAIL_MONTH columns already calculated
- Never join tables unless absolutely necessary — single table queries 
  are more reliable
- For booking window questions use AVG_BOOKING_WINDOW_DAYS from MART_OCCUPANCY
- For pricing comparison questions use MART_PRICING_SUMMARY with these exact columns:
  BRAND, REGION, CABIN_CATEGORY, LISTED_PRICE_USD, AVG_BOOKED_PRICE_USD, PRICE_VARIANCE_PCT, PRICE_POSITION
- Never use AVG_CABIN_PRICE_USD — that column does not exist
- For revenue and cabin price questions use MART_REVENUE with CABIN_PRICE_USD"""

    response = client.messages.create(
        model      = "claude-sonnet-4-5",
        max_tokens = 500,
        messages   = [{"role": "user", "content": prompt}]
    )
    sql = response.content[0].text.strip()
    sql = re.sub(r'```sql|```', '', sql).strip()
    return sql


def run_sql(sql):
    """Execute SQL against Snowflake and return results."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(sql)
    cols    = [c[0] for c in cur.description]
    rows    = cur.fetchall()
    conn.close()
    return cols, rows


def format_results(cols, rows):
    """Convert SQL results to a readable string for Claude."""
    if not rows:
        return "Query returned no results."
    lines = [" | ".join(str(c) for c in cols)]
    lines.append("-" * 60)
    for row in rows[:20]:
        lines.append(" | ".join(str(round(v, 2) if isinstance(v, float) else v)
                                for v in row))
    return "\n".join(lines)


def synthesize_answer(question, sql, results_text):
    """Ask Claude to synthesize a business answer from the results."""
    prompt = f"""You are a cruise revenue intelligence assistant for NCLH 
(Norwegian, Oceania, Regent brands).

A user asked: "{question}"

You ran this SQL query:
{sql}

The query returned these results:
{results_text}

Write a clear, specific business answer. Use the actual numbers from the results.
Be concise — 3-5 sentences maximum. Lead with the direct answer.

IMPORTANT: When writing dollar amounts, always write them as USD X.XM or USD X,XXX 
format — never use the dollar sign symbol $ as it causes formatting issues."""

    response = client.messages.create(
        model      = "claude-sonnet-4-5",
        max_tokens = 400,
        messages   = [{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def validate_question(question):
    """Check if the question is answerable with available data."""
    prompt = f"""You are a validator for a cruise revenue AI system.

The system has access to NCLH internal data only:
- Booking records for Norwegian, Oceania, and Regent brands
- Occupancy and cancellation rates by itinerary and region
- Guest profiles and lifetime value
- Onboard spend by category
- Pricing logs and variance

It does NOT have access to:
- Competitor data (Royal Caribbean, Carnival, MSC etc.)
- Future forecasts or predictions
- External market data
- News or world events

IMPORTANT: Be generous in your interpretation. Questions using casual 
language like "doing great", "performing well", "best", "worst", 
"how are we doing" should be treated as ANSWERABLE by interpreting 
them as questions about revenue, occupancy, or cancellation performance.

Only mark as NOT ANSWERABLE if the question explicitly requires 
competitor data, future predictions, or external information 
that cannot exist in an internal booking database.

Is this question answerable with the available data?
Question: "{question}"

Reply in exactly this format:
ANSWERABLE: yes or no
REASON: one sentence
SUGGESTION: if no, one alternative question they could ask instead"""

    response = client.messages.create(
        model      = "claude-sonnet-4-5",
        max_tokens = 100,
        messages   = [{"role": "user", "content": prompt}]
    )
    result = response.content[0].text.strip()

    answerable = "yes" in result.lower().split("answerable:")[1].split("\n")[0].lower()
    
    try:
        reason     = result.split("REASON:")[1].split("\n")[0].strip()
        suggestion = result.split("SUGGESTION:")[1].split("\n")[0].strip()
    except Exception:
        reason     = "Question may be outside available data scope."
        suggestion = "Try asking about NCLH brand performance, occupancy, revenue, or pricing."

    return answerable, reason, suggestion


def ask_with_sql(question):
    """Full Text-to-SQL pipeline with validation."""
    try:
        # Step 1 — validate question
        answerable, reason, suggestion = validate_question(question)

        if not answerable:
            return (
                f"I can't answer that with the available data. {reason} "
                f"Try asking: '{suggestion}'",
                "",
                ""
            )

        # Step 2 — generate and run SQL
        sql          = generate_sql(question)
        cols, rows   = run_sql(sql)
        results_text = format_results(cols, rows)

        # Step 3 — synthesize answer
        answer = synthesize_answer(question, sql, results_text)
        return answer, sql, results_text

    except Exception as e:
        return (
            f"I ran into an issue answering that. "
            f"Try rephrasing your question or ask about a specific brand, "
            f"region, or metric. (Error: {str(e)})",
            "",
            ""
        )


if __name__ == "__main__":
    questions = [
        "Which region is doing well?",
        "Which region has the highest cancellation rate?",
        "How is Norwegian brand performing in Alaska?",
        "What is the average revenue per night for Regent suites?",
        "Which cabin category generates the most onboard spend?",
        "Which loyalty tier has the highest lifetime value?",
    ]

    for q in questions:
        print(f"\nQ: {q}")
        print("-" * 60)
        answer, sql, results = ask_with_sql(q)
        print(f"SQL: {sql}")
        print(f"Answer: {answer}")
        print()