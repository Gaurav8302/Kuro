# pinecone_setup.py

import os
from pinecone import Pinecone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get your Pinecone API key
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Connect to Pinecone (client)
pc = Pinecone(api_key=PINECONE_API_KEY)

# Check the existing indexes
print("✅ Available indexes:", pc.list_indexes().names())

# Now connect to your existing index
index = pc.Index("my-chatbot-memory")

print(f"🔗 Connected to index: {index.describe_index_stats()}")
