# backend/memory/retriever.py

import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Load .env variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# Load the same embedding model used for upserting
model = SentenceTransformer("all-MiniLM-L6-v2")
# Function to retrieve memories based on a query
def retrieve_memory(query: str, top_k: int = 5) -> list:
    query_vector = model.encode(query).tolist()
    result = index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    memories = []
    for match in result.matches:
        if match.score > 0.6:  # optional threshold
            memories.append(match.metadata.get("memory", "No memory text"))
    return memories

def delete_session_chunks(session_id: str):
    index = PINECONE_INDEX_NAME
    index.delete(filter={"session_id": {"$eq": session_id}})


# # --- For testing ---

# if __name__ == "__main__":
#     query = input("🧠 Enter your query: ")
#     memories = retrieve_memory(query)

#     if memories:
#         print("\n🔍 Retrieved Memories:")
#         for i, mem in enumerate(memories):
#             print(f"{i+1}. {mem}")
#     else:
#         print("❌ No matches found or retrieval failed.")

