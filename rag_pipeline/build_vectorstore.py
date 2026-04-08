import chromadb
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_pipeline.generate_summaries import generate_all_summaries
from dotenv import load_dotenv

load_dotenv()


def build_vectorstore():
    print("Generating summaries from Snowflake...")
    documents = generate_all_summaries()

    print("\nInitializing ChromaDB...")
    client = chromadb.PersistentClient(path="./rag_pipeline/vectorstore")

    # delete existing collection if it exists
    try:
        client.delete_collection("cruise_revenue")
        print("Cleared existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name="cruise_revenue",
        metadata={"hnsw:space": "cosine"}
    )

    print(f"Embedding and indexing {len(documents)} documents...")
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch    = documents[i:i + batch_size]
        texts    = [d["text"]     for d in batch]
        metas    = [d["metadata"] for d in batch]
        ids      = [f"doc_{i + j}" for j in range(len(batch))]

        collection.add(
            documents = texts,
            metadatas = metas,
            ids       = ids
        )

        if (i // batch_size) % 5 == 0:
            print(f"  Indexed {min(i + batch_size, len(documents))}/{len(documents)} documents")

    print(f"\nVector store built successfully")
    print(f"Total documents indexed: {collection.count()}")
    return collection


if __name__ == "__main__":
    build_vectorstore()