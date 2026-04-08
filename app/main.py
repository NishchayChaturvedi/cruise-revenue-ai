import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline.rag_assistant import ask, retrieve
import chromadb
import anthropic
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title = "Cruise Revenue AI",
    page_icon  = "🚢",
    layout     = "wide"
)

st.title("🚢 Cruise Revenue AI Assistant")
st.caption("Powered by Snowflake · dbt · ChromaDB · Claude")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("About")
    st.markdown("""
    This assistant answers revenue questions about Norwegian, Oceania, 
    and Regent cruise brands using:
    - **Snowflake** — gold layer data marts
    - **dbt** — data transformations
    - **ChromaDB** — vector search
    - **Claude** — AI answer generation
    """)
    st.divider()
    st.header("Sample Questions")
    sample_questions = [
        "How is Norwegian brand performing in Alaska?",
        "Which region has the highest cancellation rate?",
        "What is the average revenue per night for Regent suites?",
        "Which cabin category generates the most onboard spend?",
        "How does Oceania pricing compare to Norwegian in the Caribbean?",
        "What is the booking window trend for Mediterranean sailings?",
    ]
    for q in sample_questions:
        if st.button(q, use_container_width=True):
            st.session_state["question"] = q

# ── Main chat interface ───────────────────────────────────────────────────────
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
        "role":    "user",
        "content": question
    })
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching cruise data and generating answer..."):
            context_docs = retrieve(question)
            context      = "\n".join([f"- {doc}" for doc in context_docs])

            prompt = f"""You are a cruise revenue intelligence assistant for Norwegian Cruise Line Holdings (NCLH), 
which operates three brands: Norwegian, Oceania, and Regent.

You have access to the following relevant data from the cruise revenue database:

{context}

Based on this data, answer the following question clearly and concisely. 
Cite specific numbers from the data. If the data doesn't fully answer 
the question, say so honestly.

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

            with st.expander("View source documents retrieved"):
                for i, doc in enumerate(context_docs):
                    st.caption(f"Source {i+1}: {doc}")

    st.session_state["messages"].append({
        "role":    "assistant",
        "content": answer
    })