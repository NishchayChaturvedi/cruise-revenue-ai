import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline.rag_assistant import retrieve
from agents.revenue_agents import detect_anomalies, generate_pricing_recommendation, escalate_for_approval
import anthropic
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title = "Cruise Revenue AI",
    page_icon  = "🚢",
    layout     = "wide"
)

st.title("🚢 Cruise Revenue AI Assistant")
st.caption("Powered by Snowflake · dbt · ChromaDB · Claude · LangGraph")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("About")
    st.markdown("""
    End-to-end AI revenue intelligence for NCLH.
    - **Snowflake** — gold layer data marts
    - **dbt** — data transformations
    - **ChromaDB** — vector search
    - **Claude** — AI answer generation
    - **LangGraph** — autonomous agents
    """)
    st.divider()
    st.header("Sample Questions")
    sample_questions = [
        "How is Norwegian brand performing in Alaska?",
        "Which region has the highest cancellation rate?",
        "What is the average revenue per night for Regent suites?",
        "Which cabin category generates the most onboard spend?",
        "How does Oceania pricing compare to Norwegian in Caribbean?",
        "What is the booking window trend for Mediterranean sailings?",
    ]
    for q in sample_questions:
        if st.button(q, use_container_width=True):
            st.session_state["question"] = q

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Revenue Q&A", "Agent Dashboard"])

# ── Tab 1: Chat ───────────────────────────────────────────────────────────────
with tab1:
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "question" not in st.session_state:
        st.session_state["question"] = ""

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a revenue question...")

    if st.session_state["question"]:
        question = st.session_state["question"]
        st.session_state["question"] = ""

    if question:
        st.session_state["messages"].append({
            "role": "user", "content": question
        })
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching cruise data..."):
                context_docs = retrieve(question)
                context      = "\n".join([f"- {doc}" for doc in context_docs])

                prompt = f"""You are a cruise revenue intelligence assistant for NCLH
(Norwegian, Oceania, Regent brands).

Relevant data from cruise revenue database:
{context}

Answer clearly with specific numbers. If data is insufficient, say so.

Question: {question}
Answer:"""

                client   = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                response = client.messages.create(
                    model      = "claude-sonnet-4-5",
                    max_tokens = 600,
                    messages   = [{"role": "user", "content": prompt}]
                )
                answer = response.content[0].text
                st.markdown(answer)

                with st.expander("View source documents"):
                    for i, doc in enumerate(context_docs):
                        st.caption(f"Source {i+1}: {doc}")

        st.session_state["messages"].append({
            "role": "assistant", "content": answer
        })

# ── Tab 2: Agent Dashboard ────────────────────────────────────────────────────
with tab2:
    st.subheader("Revenue Anomaly Detection Agent")
    st.markdown("Click the button below to run the full agent pipeline against your Snowflake data.")

    if "agent_actions" not in st.session_state:
        st.session_state["agent_actions"] = []

    if "anomaly_results" not in st.session_state:
        st.session_state["anomaly_results"] = []

    # button lives inside tab2 now
    if st.button("Run Anomaly Detection", type="primary"):
        with st.spinner("Agent 1 scanning Snowflake for revenue anomalies..."):
            anomalies = detect_anomalies()
            st.session_state["anomaly_results"] = anomalies

    # show results if we have them
    if st.session_state["anomaly_results"]:
        anomalies = st.session_state["anomaly_results"]
        st.warning(f"Found {len(anomalies)} anomalies. Showing top 3.")

        for i, anomaly in enumerate(anomalies[:3]):
            with st.expander(
                f"ANOMALY {i+1}: {anomaly['brand']} — "
                f"{anomaly['itinerary_name']} "
                f"(Occupancy: {anomaly['avg_occupancy']}%)",
                expanded=True
            ):
                col1, col2, col3 = st.columns(3)
                col1.metric("Occupancy",         f"{anomaly['avg_occupancy']}%")
                col2.metric("Cancellation Rate", f"{anomaly['avg_cancellation']}%")
                col3.metric("Total Revenue",     f"${anomaly['total_revenue']:,.0f}")

                if st.button(f"Generate Recommendation", key=f"btn_rec_{i}"):
                    with st.spinner("Agent 2 generating pricing recommendation..."):
                        rec    = generate_pricing_recommendation(anomaly)
                        action = escalate_for_approval(anomaly, rec)
                        st.session_state[f"result_rec_{i}"]    = rec
                        st.session_state[f"result_action_{i}"] = action

                if st.session_state.get(f"result_rec_{i}"):
                    st.markdown("**AI Pricing Recommendation:**")
                    st.markdown(st.session_state[f"result_rec_{i}"])
                    
                    col_a, col_b = st.columns(2)
                    if col_a.button("Approve", key=f"approve_{i}", type="primary"):
                        action = st.session_state[f"result_action_{i}"]
                        action['status'] = 'APPROVED'
                        st.session_state["agent_actions"].append(action)
                        st.success(f"Action {action['action_id']} approved")

                    if col_b.button("Reject", key=f"reject_{i}"):
                        action = st.session_state[f"result_action_{i}"]
                        action['status'] = 'REJECTED'
                        st.session_state["agent_actions"].append(action)
                        st.error(f"Action {action['action_id']} rejected")

    if st.session_state["agent_actions"]:
        st.divider()
        st.subheader("Action Log")
        for action in st.session_state["agent_actions"]:
            status_color = "green" if action['status'] == 'APPROVED' else "red"
            st.markdown(
                f"**{action['action_id']}** — "
                f"{action['brand']} {action['itinerary']} — "
                f":{status_color}[{action['status']}]"
            )