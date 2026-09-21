#!/usr/bin/env python3
"""Reset Kuro demo MongoDB + Pinecone state and ensure a 768-d index exists.

Usage (from repo root, with env loaded):
  cd backend && python ../scripts/reset_demo_data.py

Requires: MONGODB_URI, PINECONE_API_KEY, and optionally PINECONE_INDEX_NAME.
Does NOT print secret values.
"""
from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
load_dotenv(os.path.join(BACKEND, ".env"))
load_dotenv(os.path.join(ROOT, ".env"))

from config.embeddings import (  # noqa: E402
    DEFAULT_PINECONE_INDEX,
    EMBEDDING_DIMENSION,
    EMBEDDING_METRIC,
    EMBEDDING_MODEL,
)


def reset_mongodb() -> None:
    from pymongo import MongoClient

    uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    if not uri:
        raise SystemExit("MONGODB_URI is required to reset MongoDB demo data")

    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    db_name = "chatbot_db"
    db = client[db_name]
    collections = db.list_collection_names()
    print(f"MongoDB database={db_name} collections={collections}")

    # Application collections used by Kuro (demo data only)
    targets = [
        "chats",
        "chat_sessions",
        "session_titles",
        "sessions",
        "memories",
        "memories_v3",
        "llm_calls",
        "user_profiles",
        "users",
    ]
    for name in targets:
        if name in collections:
            result = db[name].delete_many({})
            print(f"  cleared {name}: deleted={result.deleted_count}")
        else:
            print(f"  skip missing collection {name}")
    client.close()
    print("MongoDB demo data reset complete")


def ensure_pinecone_index() -> None:
    from pinecone import Pinecone, ServerlessSpec

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise SystemExit("PINECONE_API_KEY is required to reset Pinecone")

    index_name = os.getenv("PINECONE_INDEX_NAME", DEFAULT_PINECONE_INDEX)
    pc = Pinecone(api_key=api_key)
    existing = {idx["name"] for idx in pc.list_indexes()}

    if index_name in existing:
        desc = pc.describe_index(index_name)
        dim = getattr(desc, "dimension", None)
        if dim is None and isinstance(desc, dict):
            dim = desc.get("dimension")
        print(f"Pinecone index '{index_name}' exists dimension={dim}")
        if dim is not None and int(dim) != EMBEDDING_DIMENSION:
            print(
                f"  dimension {dim} != required {EMBEDDING_DIMENSION}; deleting and recreating"
            )
            pc.delete_index(index_name)
            # wait for deletion
            for _ in range(30):
                time.sleep(2)
                if index_name not in {i["name"] for i in pc.list_indexes()}:
                    break
            existing.discard(index_name)
        else:
            # Wipe vectors in place
            index = pc.Index(index_name)
            try:
                index.delete(delete_all=True)
                print(f"  wiped all vectors in '{index_name}'")
            except Exception as exc:
                print(f"  wipe warning: {exc}")
            print(
                f"Pinecone ready: index={index_name} dim={EMBEDDING_DIMENSION} "
                f"metric={EMBEDDING_METRIC} embedding={EMBEDDING_MODEL}"
            )
            return

    if index_name not in existing:
        cloud = os.getenv("PINECONE_CLOUD", "aws")
        region = os.getenv("PINECONE_REGION", "us-east-1")
        print(
            f"Creating Pinecone index '{index_name}' "
            f"dim={EMBEDDING_DIMENSION} metric={EMBEDDING_METRIC} "
            f"cloud={cloud} region={region}"
        )
        pc.create_index(
            name=index_name,
            dimension=EMBEDDING_DIMENSION,
            metric=EMBEDDING_METRIC,
            spec=ServerlessSpec(cloud=cloud, region=region),
        )
        for _ in range(60):
            desc = pc.describe_index(index_name)
            status = getattr(desc, "status", None)
            ready = False
            if status is not None:
                ready = getattr(status, "ready", False) or (
                    isinstance(status, dict) and status.get("ready")
                )
            if ready:
                break
            time.sleep(2)
        print(f"Pinecone index '{index_name}' ready")

    print(
        f"Pinecone ready: index={index_name} dim={EMBEDDING_DIMENSION} "
        f"metric={EMBEDDING_METRIC} embedding={EMBEDDING_MODEL}"
    )


def main() -> None:
    print("=== Kuro demo data reset ===")
    print(f"Embedding model={EMBEDDING_MODEL} dim={EMBEDDING_DIMENSION}")
    reset_mongodb()
    ensure_pinecone_index()
    print("Done.")


if __name__ == "__main__":
    main()
