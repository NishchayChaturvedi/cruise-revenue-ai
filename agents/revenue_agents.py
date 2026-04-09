import os
import sys
import json
import anthropic
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_pipeline.rag_assistant import retrieve

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


def detect_anomalies():
    print("\n[AGENT 1 — Anomaly Detector] Scanning revenue data...")
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT
            brand,
            region,
            itinerary_name,
            sail_year,
            sail_quarter,
            ROUND(AVG(occupancy_rate_pct), 2)    as avg_occupancy,
            ROUND(AVG(cancellation_rate_pct), 2) as avg_cancellation,
            ROUND(SUM(total_revenue_usd), 2)     as total_revenue,
            SUM(total_bookings)                  as total_bookings
        FROM MARTS.MART_OCCUPANCY
        GROUP BY 1,2,3,4,5
        ORDER BY avg_occupancy ASC
        LIMIT 20
    """)
    cols = [c[0].lower() for c in cur.description]
    rows = cur.fetchall()
    conn.close()

    anomalies = []
    for row in rows:
        rec = dict(zip(cols, row))
        if rec['avg_occupancy'] < 70 or rec['avg_cancellation'] > 15:
            anomalies.append(rec)

    if anomalies:
        print(f"  Found {len(anomalies)} anomalies")
        for a in anomalies[:3]:
            print(f"  ALERT: {a['brand']} {a['itinerary_name']} "
                  f"— occupancy {a['avg_occupancy']}%, "
                  f"cancellation {a['avg_cancellation']}%")
    else:
        print("  No critical anomalies detected")

    return anomalies


def generate_pricing_recommendation(anomaly):
    print(f"\n[AGENT 2 — Pricing Advisor] Analyzing {anomaly['brand']} "
          f"{anomaly['itinerary_name']}...")

    context_docs = retrieve(
        f"{anomaly['brand']} {anomaly['region']} "
        f"{anomaly['itinerary_name']} pricing occupancy"
    )
    context = "\n".join([f"- {d}" for d in context_docs])

    prompt = f"""You are a cruise revenue pricing advisor.

A revenue anomaly has been detected:
- Brand: {anomaly['brand']}
- Itinerary: {anomaly['itinerary_name']}
- Region: {anomaly['region']}
- Current occupancy: {anomaly['avg_occupancy']}%
- Cancellation rate: {anomaly['avg_cancellation']}%
- Total revenue: ${anomaly['total_revenue']:,.2f}

Relevant market context:
{context}

Provide a specific pricing recommendation to improve occupancy.
Include: recommended price adjustment (%), rationale, expected impact.
Keep response under 150 words."""

    response = client.messages.create(
        model      = "claude-sonnet-4-5",
        max_tokens = 200,
        messages   = [{"role": "user", "content": prompt}]
    )
    recommendation = response.content[0].text
    print(f"  Recommendation generated")
    return recommendation


def escalate_for_approval(anomaly, recommendation):
    print(f"\n[AGENT 3 — Escalator] Preparing approval request...")

    action = {
        "timestamp":         datetime.now().isoformat(),
        "brand":             anomaly['brand'],
        "itinerary":         anomaly['itinerary_name'],
        "region":            anomaly['region'],
        "current_occupancy": anomaly['avg_occupancy'],
        "cancellation_rate": anomaly['avg_cancellation'],
        "recommendation":    recommendation,
        "status":            "PENDING_APPROVAL",
        "action_id":         f"ACT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }

    print(f"\n{'='*60}")
    print("REVENUE ACTION — REQUIRES HUMAN APPROVAL")
    print(f"{'='*60}")
    print(f"Action ID  : {action['action_id']}")
    print(f"Brand      : {action['brand']}")
    print(f"Itinerary  : {action['itinerary']}")
    print(f"Region     : {action['region']}")
    print(f"Occupancy  : {action['current_occupancy']}%")
    print(f"Cancel Rate: {action['cancellation_rate']}%")
    print(f"\nRecommendation:\n{action['recommendation']}")
    print(f"{'='*60}")

    return action


def run_agent_pipeline(auto_approve=False):
    print("\nCRUISE REVENUE AGENT PIPELINE")
    print("="*60)
    print("Starting autonomous revenue monitoring...\n")

    anomalies = detect_anomalies()
    if not anomalies:
        print("\nNo anomalies found. Pipeline complete.")
        return []

    actions = []
    for anomaly in anomalies[:2]:
        rec    = generate_pricing_recommendation(anomaly)
        action = escalate_for_approval(anomaly, rec)

        if auto_approve:
            action['status'] = 'APPROVED'
            print("Auto-approved for demo purposes")
        else:
            approval = input("\nApprove this action? (yes/no): ").strip().lower()
            action['status'] = 'APPROVED' if approval == 'yes' else 'REJECTED'
            print(f"Action {action['status']}")

        actions.append(action)

    print(f"\nPipeline complete. {len(actions)} actions processed.")
    return actions


if __name__ == "__main__":
    actions = run_agent_pipeline(auto_approve=True)
    print(f"\nFinal actions log:")
    for a in actions:
        print(f"  {a['action_id']} — {a['brand']} {a['itinerary']} — {a['status']}")