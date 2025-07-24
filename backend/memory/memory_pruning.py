"""
Memory Pruning and Summarization Module

This module handles periodic pruning and summarization of memories
to prevent database bloat and maintain efficient retrieval.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from backend.memory.memory_manager import MemoryManager, get_relevant_memories
from backend.memory.chat_database import ChatDatabase

logger = logging.getLogger(__name__)

class MemoryPruningManager:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.chat_db = ChatDatabase()

    async def summarize_old_memories(self, user_id: str, days_threshold: int = 30) -> None:
        """
        Summarize memories older than the threshold and create a condensed version
        """
        try:
            # Get old memories
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            old_memories = self.memory_manager.get_memories_before_date(user_id, cutoff_date)

            if not old_memories:
                return

            # Create summary chunks of related memories
            memory_clusters = self._cluster_related_memories(old_memories)

            # Summarize each cluster
            for cluster in memory_clusters:
                summary = self._generate_cluster_summary(cluster)
                
                # Store the summary as a new memory
                metadata = {
                    "user": user_id,
                    "type": "memory_summary",
                    "original_count": len(cluster),
                    "date_range": f"{cluster[0]['timestamp']} to {cluster[-1]['timestamp']}",
                    "summarized_at": datetime.utcnow()
                }
                self.memory_manager.store_memory(summary, metadata)

            # Delete the old memories after successful summarization
            memory_ids = [mem["id"] for cluster in memory_clusters for mem in cluster]
            self.memory_manager.delete_memories(memory_ids)

            logger.info(f"Successfully summarized {len(memory_ids)} old memories for user {user_id}")

        except Exception as e:
            logger.error(f"Error summarizing memories: {str(e)}")

    def _cluster_related_memories(self, memories: List[Dict[str, Any]], similarity_threshold: float = 0.7) -> List[List[Dict[str, Any]]]:
        """Group related memories together based on semantic similarity"""
        clusters = []
        for memory in memories:
            added_to_cluster = False
            memory_embedding = self.memory_manager.embed_text(memory["text"])

            for cluster in clusters:
                # Compare with first memory in cluster as representative
                cluster_embedding = self.memory_manager.embed_text(cluster[0]["text"])
                similarity = self._compute_similarity(memory_embedding, cluster_embedding)

                if similarity > similarity_threshold:
                    cluster.append(memory)
                    added_to_cluster = True
                    break

            if not added_to_cluster:
                clusters.append([memory])

        return clusters

    def _compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        import numpy as np
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def _generate_cluster_summary(self, memories: List[Dict[str, Any]]) -> str:
        """Generate a concise summary of related memories"""
        from backend.memory.chat_manager import ChatManager

        # Sort memories by timestamp
        sorted_memories = sorted(memories, key=lambda x: x["timestamp"])
        
        # Create a prompt for the AI to summarize
        memory_texts = [m["text"] for m in sorted_memories]
        prompt = f"""Please create a concise summary of these related memories, preserving key information:

{memory_texts}

Summary (be brief but include key details):"""

        # Generate summary using the chat manager's AI model
        chat_manager = ChatManager()
        summary = chat_manager.generate_ai_response(prompt)
        
        return summary
