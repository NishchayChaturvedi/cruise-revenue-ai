import chromadb
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client    = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
db_client = chromadb.PersistentClient(path="./rag_pipeline/vectorstore")
collection = db_client.get_collection("cruise_revenue")


def retrieve(question, n_results=6):
    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )
    return results["documents"][0]


def ask(question):
    print(f"\nQuestion: {question}")
    print("Retrieving relevant context...")

    context_docs = retrieve(question)
    context      = "\n".join([f"- {doc}" for doc in context_docs])

    prompt = f"""You are a cruise revenue intelligence assistant for Norwegian Cruise Line Holdings (NCLH), 
which operates three brands: Norwegian, Oceania, and Regent.

You have access to the following relevant data from the cruise revenue database:

{context}

Based on this data, answer the following question clearly and concisely. 
Cite specific numbers from the data. If the data doesn't fully answer the question, say so.

Question: {question}

Answer:"""

    print("Generating answer with Claude...")
    response = client.messages.create(
        model      = "claude-sonnet-4-5",
        max_tokens = 500,
        messages   = [{"role": "user", "content": prompt}]
    )

    answer = response.content[0].text
    print(f"\nAnswer:\n{answer}")
    print("\n" + "─"*60)
    return answer


if __name__ == "__main__":
    print("Cruise Revenue AI Assistant")
    print("="*60)

    test_questions = [
        "How is Norwegian brand performing in Alaska?",
        "Which region has the highest cancellation rate?",
        "What is the average revenue per night for Regent suites?",
        "Which cabin category generates the most onboard spend?",
    ]

    for question in test_questions:
        ask(question)