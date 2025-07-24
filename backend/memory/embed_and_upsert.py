# embed_and_upsert.py

from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import os
from uuid import uuid4
from dotenv import load_dotenv
load_dotenv()  # <-- This is required to load the .env file

from pinecone import Pinecone


# 1. Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")  # Light and fast; good for most use cases

# 2. Pinecone initialization
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "my-chatbot-memory"

pc = Pinecone(api_key=PINECONE_API_KEY)

# Connect or create index
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=384,  # dimension for all-MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(PINECONE_INDEX_NAME)

# 3. Embedding function
def embed_text(text: str) -> list[float]:
    return embed_model.encode([text])[0].tolist()

# 4. Upsert memory into Pinecone
def upsert_memory(text: str, metadata: dict):
    vector = embed_text(text)
    vector_id = str(uuid4())

    index.upsert(
        vectors=[
            {
                "id": vector_id,
                "values": vector,
                "metadata": metadata
            }
        ]
    )
    print(f"✅ Memory upserted with ID: {vector_id}")

# 5. Example usage
if __name__ == "__main__":
    sample_text = "I had a conversation about building a personal AI chatbot and my name is Gummy. I love photography and I want to learn more about AI."
    sample_metadata = {
    "user": "gummy",
    "type": "chat",
    "source": "memory",
    "memory": sample_text  # ✅ this line is crucial
    }

    upsert_memory(sample_text, sample_metadata)
