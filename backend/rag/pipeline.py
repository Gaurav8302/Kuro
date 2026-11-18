"""
RAG Pipeline — Retrieval-Augmented Generation for Kuro AI.

Maps the actual production retrieval path, provides ingestion security,
chunking with provenance, evaluation metrics, and grounded generation.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
import hashlib
import mimetypes
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Literal, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

# Optional imports for document processing
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# Import embed_text from existing pinecone module
from db.pinecone import embed_text, query_vectors

logger = logging.getLogger(__name__)


# =============================================================================
# RAG PATH MAPPING — Documents the actual production retrieval flow
# =============================================================================

class RetrievalPath(Enum):
    """Documents which retrieval path is active in production."""
    MEMORY_RETRIEVER = "memory_retriever"      # memory/retriever.py
    LONG_TERM_MEMORY = "long_term_memory"      # memory/long_term_memory.py
    MEMORY_UPDATER = "memory_updater"          # memory/updater.py (async background)
    CHAT_MANAGER_V3 = "chat_manager_v3"        # memory/chat_manager_v3.py (main chat flow)
    SESSION_MEMORY = "session_memory"          # memory/session_memory.py (Layer 1)
    LEGACY_PINECONE = "legacy_pinecone"        # memory/ultra_lightweight_memory.py (fallback)


@dataclass
class ActiveRetrievalConfig:
    """Configuration of the active retrieval path."""
    primary_path: RetrievalPath = RetrievalPath.CHAT_MANAGER_V3
    fallback_paths: List[RetrievalPath] = field(default_factory=lambda: [
        RetrievalPath.MEMORY_RETRIEVER,
        RetrievalPath.LONG_TERM_MEMORY,
        RetrievalPath.SESSION_MEMORY,
    ])
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768
    pinecone_index: str = "kuro-memory"
    similarity_threshold: float = 0.75
    top_k_default: int = 5
    rerank_enabled: bool = True
    citation_validation: bool = True


# Global config instance
_active_retrieval_config = ActiveRetrievalConfig()


def get_active_retrieval_config() -> ActiveRetrievalConfig:
    """Get the active retrieval configuration."""
    return _active_retrieval_config


def describe_retrieval_path() -> Dict[str, Any]:
    """Describe the active retrieval path for documentation/auditing."""
    config = get_active_retrieval_config()
    return {
        "primary_path": config.primary_path.value,
        "fallback_paths": [p.value for p in config.fallback_paths],
        "embedding_model": config.embedding_model,
        "embedding_dimension": config.embedding_dimension,
        "pinecone_index": config.pinecone_index,
        "similarity_threshold": config.similarity_threshold,
        "top_k_default": config.top_k_default,
        "rerank_enabled": config.rerank_enabled,
        "citation_validation": config.citation_validation,
        "components": {
            "chat_manager_v3": "memory/chat_manager_v3.py (main chat flow)",
            "memory_retriever": "memory/retriever.py (vector retrieval + rerank)",
            "long_term_memory": "memory/long_term_memory.py (session summaries)",
            "session_memory": "memory/session_memory.py (Layer 1 recent messages)",
            "memory_updater": "memory/updater.py (async background extraction)",
            "legacy_pinecone": "memory/ultra_lightweight_memory.py (fallback)",
        }
    }


# =============================================================================
# INGESTION SECURITY
# =============================================================================

class IngestionSecurityError(Exception):
    """Raised when ingestion security checks fail."""
    pass


class IngestionValidator:
    """Validates and sanitizes documents for ingestion."""
    
    # Maximum file sizes (bytes)
    MAX_FILE_SIZES = {
        "application/pdf": 50 * 1024 * 1024,      # 50 MB
        "text/plain": 10 * 1024 * 1024,           # 10 MB
        "text/markdown": 10 * 1024 * 1024,
        "application/json": 5 * 1024 * 1024,      # 5 MB
        "text/csv": 10 * 1024 * 1024,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 50 * 1024 * 1024,  # DOCX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": 20 * 1024 * 1024,  # XLSX
    }
    
    # Maximum pages for PDFs
    MAX_PDF_PAGES = 200
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = set(MAX_FILE_SIZES.keys())
    
    # Dangerous extensions that should never be processed
    DANGEROUS_EXTENSIONS = {
        ".exe", ".bat", ".sh", ".py", ".js", ".php", ".jar", ".war",
        ".scr", ".com", ".pif", ".vbs", ".wsf", ".msi", ".app",
        ".dmg", ".iso", ".zip", ".tar", ".gz", ".rar", ".7z",
    }
    
    @classmethod
    def validate_file(cls, file_content: bytes, filename: str, mime_type: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate a file for ingestion.
        
        Returns: (is_valid, error_message)
        """
        # Check file extension
        ext = Path(filename).suffix.lower()
        if ext in cls.DANGEROUS_EXTENSIONS:
            return False, f"Dangerous file extension: {ext}"
        
        # Detect MIME type if not provided
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type is None:
                mime_type = "application/octet-stream"
        
        # Check MIME type
        if mime_type not in cls.ALLOWED_MIME_TYPES:
            return False, f"Unsupported file type: {mime_type}"
        
        # Check file size
        max_size = cls.MAX_FILE_SIZES.get(mime_type, 10 * 1024 * 1024)
        if len(file_content) > max_size:
            return False, f"File too large: {len(file_content)} bytes (max {max_size})"
        
        # Check for empty file
        if len(file_content) == 0:
            return False, "Empty file"
        
        return True, ""
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove path components
        name = Path(filename).name
        # Remove dangerous characters
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        # Limit length
        if len(name) > 255:
            name = name[:255]
        return name


# =============================================================================
# CHUNKING WITH PROVENANCE
# =============================================================================

class ChunkingConfig:
    """Configuration for document chunking."""
    CHUNK_SIZE = 1000          # Target tokens per chunk
    CHUNK_OVERLAP = 200        # Overlap tokens
    MIN_CHUNK_SIZE = 100       # Minimum viable chunk
    MAX_CHUNKS_PER_DOC = 500   # Safety limit


@dataclass
class DocumentChunk:
    """A chunk of a document with full provenance."""
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    chunk_index: int = 0
    text: str = ""
    token_count: int = 0
    char_start: int = 0
    char_end: int = 0
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert to Pinecone-compatible metadata."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text[:2000],  # Pinecone metadata limit
            "token_count": self.token_count,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "provenance": json.dumps(self.provenance),
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "created_at": self.created_at.isoformat(),
        }


class DocumentChunker:
    """Chunks documents with provenance tracking."""
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
    
    def chunk_text(
        self,
        text: str,
        document_id: str,
        provenance: Dict[str, Any],
        section_titles: Optional[List[Tuple[int, str]]] = None,
    ) -> List[DocumentChunk]:
        """
        Chunk text into overlapping segments with provenance.
        
        Args:
            text: Full document text
            document_id: Unique document identifier
            provenance: Document provenance metadata
            section_titles: List of (char_offset, title) for section tracking
            
        Returns:
            List of DocumentChunk objects
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        words = text.split()
        chunk_size = self.config.CHUNK_SIZE
        overlap = self.config.CHUNK_OVERLAP
        
        # Simple word-based chunking with small-document protection
        step = max(1, chunk_size - overlap)
        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            if not chunk_words:
                break
            # Only break for small tail if we already produced at least one chunk
            if len(chunk_words) < self.config.MIN_CHUNK_SIZE and chunks:
                break
            
            chunk_text = " ".join(chunk_words)
            char_start = len(" ".join(words[:i]))
            char_end = char_start + len(chunk_text)
            
            # Find section title for this chunk
            section_title = None
            if section_titles:
                for offset, title in section_titles:
                    if offset <= char_start:
                        section_title = title
                    else:
                        break
            
            # Calculate page number (approximate)
            page_number = max(1, char_start // 3000 + 1)  # ~3000 chars per page
            
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=len(chunks),
                text=chunk_text,
                token_count=len(chunk_words),
                char_start=char_start,
                char_end=char_end,
                page_number=page_number,
                section_title=section_title,
                provenance={
                    **provenance,
                    "chunking_method": "word_overlap",
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                }
            )
            chunks.append(chunk)
            
            if len(chunks) >= self.config.MAX_CHUNKS_PER_DOC:
                logger.warning(f"Document {document_id} exceeded max chunks, truncating")
                break
        
        return chunks


# =============================================================================
# DOCUMENT PROCESSING
# =============================================================================

class DocumentProcessor:
    """Processes documents for RAG ingestion."""
    
    def __init__(self):
        self.validator = IngestionValidator()
        self.chunker = DocumentChunker()

    def ingest_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience alias for process_document."""
        return self.process_document(
            file_content=file_content,
            filename=filename,
            user_id=user_id,
            mime_type=mime_type,
            metadata=metadata,
        )

    def process_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a document for RAG ingestion.
        
        Returns dict with: document_id, chunks, metadata, errors
        """
        # Validate
        safe_filename = IngestionValidator.sanitize_filename(filename)
        is_valid, error = IngestionValidator.validate_file(file_content, safe_filename, mime_type)
        if not is_valid:
            raise IngestionSecurityError(error)
        
        document_id = str(uuid.uuid4())
        
        # Extract text based on MIME type
        mime_type = mime_type or mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"
        text, page_info = self._extract_text(file_content, mime_type)
        
        if not text or not text.strip():
            raise IngestionSecurityError("No extractable text found in document")
        
        # Build provenance
        provenance = {
            "source_filename": safe_filename,
            "original_filename": filename,
            "mime_type": mime_type,
            "file_size": len(file_content),
            "file_hash": hashlib.sha256(file_content).hexdigest(),
            "user_id": user_id,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "mime_type": mime_type,
            **(metadata or {}),
        }
        
        # Chunk
        chunker = DocumentChunker()
        chunks = chunker.chunk_text(text, document_id, provenance)
        
        # Generate embeddings and store in Pinecone
        vectors_to_upsert = []
        for chunk in chunks:
            chunk.embedding = embed_text(chunk.text, task_type="retrieval_document")
            chunk.embedding_model = "gemini-embedding-001"
            chunk.embedding_dim = 768
            chunk.provenance["user_id"] = user_id

            meta = {
                "id": chunk.chunk_id,
                "document_id": document_id,
                "chunk_id": chunk.chunk_id,
                "text": chunk.text[:2000],
                "content": chunk.text[:2000],
                "user_id": user_id,
                "user": user_id,
                "type": "document_chunk",
                "category": "document_chunk",
                "filename": safe_filename,
                "importance": 7.0,
                "page_number": chunk.page_number or 1,
            }
            vectors_to_upsert.append((chunk.chunk_id, chunk.embedding, meta))

        try:
            from db.pinecone import _get_index
            index = _get_index()
            if index and vectors_to_upsert:
                for i in range(0, len(vectors_to_upsert), 100):
                    index.upsert(vectors=vectors_to_upsert[i : i + 100])
                logger.info("Upserted %d document chunks to Pinecone for doc %s", len(vectors_to_upsert), document_id)
        except Exception as e:
            logger.error("Failed to upsert document chunks to Pinecone: %s", e)
        
        return {
            "document_id": document_id,
            "filename": safe_filename,
            "original_filename": filename,
            "mime_type": mime_type,
            "file_size": len(file_content),
            "file_hash": provenance["file_hash"],
            "page_count": page_info.get("page_count", 0),
            "chunk_count": len(chunks),
            "total_tokens": sum(c.token_count for c in chunks),
            "chunks": [c.to_metadata() for c in chunks],
            "provenance": provenance,
        }
    
    def _extract_text(self, content: bytes, mime_type: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from various file types."""
        if mime_type == "text/plain" or mime_type == "text/markdown":
            return content.decode("utf-8", errors="replace"), {"page_count": 1}
        
        elif mime_type == "application/pdf":
            return self._extract_pdf_text(content)
        
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._extract_docx_text(content)
        
        elif mime_type == "application/json":
            try:
                return json.dumps(json.loads(content), indent=2), {"page_count": 1}
            except:
                return content.decode("utf-8", errors="replace"), {"page_count": 1}
        
        elif mime_type == "text/csv":
            return content.decode("utf-8", errors="replace"), {"page_count": 1}
        
        else:
            # Fallback: try to decode as text
            return content.decode("utf-8", errors="replace"), {"page_count": 1}
    
    def _extract_pdf_text(self, content: bytes) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF with page tracking."""
        try:
            import pdfplumber
            with pdfplumber.open(content) as pdf:
                pages = []
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(f"--- Page {i+1} ---\n{text}")
                
                if len(pdf.pages) > 200:
                    logger.warning(f"PDF has {len(pdf.pages)} pages, exceeds limit of 200")
                
                return "\n\n".join(pages), {"page_count": len(pdf.pages)}
        except ImportError:
            logger.warning("pdfplumber not available, using fallback")
            return content.decode("utf-8", errors="replace"), {"page_count": 1}
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise IngestionSecurityError(f"Failed to extract PDF text: {e}")
    
    def _extract_docx_text(self, content: bytes) -> Tuple[str, Dict[str, Any]]:
        """Extract text from DOCX."""
        try:
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs), {"page_count": 1}
        except ImportError:
            logger.warning("python-docx not available")
            return "", {"page_count": 0}
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise IngestionSecurityError(f"Failed to extract DOCX text: {e}")


# =============================================================================
# RETRIEVAL QUALITY EVALUATION
# =============================================================================

@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality evaluation."""
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)
    context_precision: float = 0.0
    context_recall: float = 0.0
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    faithfulness: float = 0.0
    abstention_rate: float = 0.0
    cross_tenant_leakage: float = 0.0


class RetrievalEvaluator:
    """Evaluates retrieval quality against a labeled dataset."""
    
    def __init__(self, retriever_fn, k_values: List[int] = [1, 3, 5, 10]):
        self.retriever_fn = retriever_fn
        self.k_values = k_values
    
    def evaluate(
        self,
        test_cases: List[Dict[str, Any]],
        user_id: str = "eval_user",
    ) -> RetrievalMetrics:
        """
        Evaluate retrieval against test cases.
        
        test_cases format:
        [
            {
                "query": "What did we discuss about Python?",
                "relevant_chunk_ids": ["chunk_1", "chunk_2"],
                "relevant_doc_ids": ["doc_1"],
                "expected_answer": "We discussed Python async patterns..."
            }
        ]
        """
        metrics = RetrievalMetrics()
        total_queries = len(test_cases)
        reciprocal_ranks: List[float] = []
        ndcg_scores: Dict[int, List[float]] = {k: [] for k in self.k_values}
        
        for case in test_cases:
            query = case["query"]
            relevant_chunk_ids = set(case.get("relevant_chunk_ids", []))
            relevant_doc_ids = set(case.get("relevant_doc_ids", []))
            
            # Retrieve
            results = self.retriever_fn(query, user_id=user_id)
            retrieved_chunk_ids = [r.get("metadata", {}).get("chunk_id") for r in results]
            retrieved_doc_ids = [r.get("metadata", {}).get("document_id") for r in results]
            
            # Compute metrics for each k
            for k in self.k_values:
                top_k_chunks = retrieved_chunk_ids[:k]
                top_k_docs = retrieved_doc_ids[:k]
                
                # Recall@k
                recall = len(relevant_chunk_ids & set(top_k_chunks)) / max(len(relevant_chunk_ids), 1)
                metrics.recall_at_k.setdefault(k, []).append(recall)
                
                # Precision@k
                precision = len(relevant_chunk_ids & set(top_k_chunks)) / max(k, 1)
                metrics.precision_at_k.setdefault(k, []).append(precision)
                
                # nDCG@k
                ndcg = self._compute_ndcg(top_k_chunks, relevant_chunk_ids, k)
                ndcg_scores[k].append(ndcg)
            
            # MRR (Mean Reciprocal Rank)
            for i, chunk_id in enumerate(retrieved_chunk_ids):
                if chunk_id in relevant_chunk_ids:
                    reciprocal_ranks.append(1.0 / (i + 1))
                    break
            else:
                reciprocal_ranks.append(0.0)
        
        # Aggregate
        for k in self.k_values:
            recall_vals = metrics.recall_at_k.get(k, [0.0])
            metrics.recall_at_k[k] = sum(recall_vals) / max(len(recall_vals), 1)
            
            precision_vals = metrics.precision_at_k.get(k, [0.0])
            metrics.precision_at_k[k] = sum(precision_vals) / max(len(precision_vals), 1)
            
            ndcg_vals = ndcg_scores.get(k, [0.0])
            metrics.ndcg_at_k[k] = sum(ndcg_vals) / max(len(ndcg_vals), 1)
        
        metrics.mrr = sum(reciprocal_ranks) / max(len(reciprocal_ranks), 1)
        
        return metrics
    
    def _compute_ndcg(self, retrieved: List[str], relevant: set, k: int) -> float:
        """Compute nDCG@k."""
        if not relevant:
            return 0.0
        
        # DCG
        dcg = 0.0
        for i, item in enumerate(retrieved[:k]):
            if item in relevant:
                dcg += 1.0 / (i + 2).bit_length()  # log2(i+2)
        
        # IDCG (ideal)
        idcg = sum(1.0 / (i + 2).bit_length() for i in range(min(len(relevant), k)))
        
        return dcg / idcg if idcg > 0 else 0.0


# =============================================================================
# GROUNDED GENERATION & CITATION VALIDATION
# =============================================================================

class GroundedGenerator:
    """Generates responses with citation validation."""
    
    def __init__(self):
        self.citation_pattern = re.compile(r'\[(\d+(?:,\s*\d+)*)\]')
        self.source_citation_pattern = re.compile(r'\(source\s*:\s*[^\)]+\)', re.IGNORECASE)
    
    def validate_citations(
        self,
        response: str,
        sources: List[Dict[str, Any]],
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate that all citations in response reference actual sources.
        
        Returns: (is_valid, missing_citations, extra_citations)
        """
        # Find all citations in response
        citation_matches = self.citation_pattern.findall(response)
        cited_indices = set()
        for match in citation_matches:
            for num in match.split(","):
                try:
                    cited_indices.add(int(num.strip()) - 1)  # Convert to 0-based
                except ValueError:
                    pass
        
        # Check if all cited indices exist in sources
        missing = []
        for idx in cited_indices:
            if idx >= len(sources):
                missing.append(f"[{idx + 1}]")
        
        # Check for source citations not referenced
        extra = []
        for i, source in enumerate(sources):
            if i not in cited_indices:
                # Check if source content appears in response without citation
                source_text = source.get("text", "")[:100]
                if source_text and source_text.lower() in response.lower():
                    extra.append(f"[{i + 1}]")
        
        is_valid = len(missing) == 0
        return is_valid, missing, extra
    
    def validate_grounding(
        self,
        response: str,
        sources: List[Dict[str, Any]],
        query: str,
    ) -> Dict[str, Any]:
        """
        Validate that response is grounded in provided sources.
        
        Returns dict with validation results.
        """
        valid, missing, extra = self.validate_citations(response, sources)
        
        # Check for hallucination indicators
        hallucination_signals = [
            r"(?i)\b(?:according to|studies show|research indicates|experts agree)\b",
            r"(?i)\b(?:definitely|certainly|absolutely)\b",
        ]
        
        hallucination_count = 0
        for pattern in hallucination_signals:
            hallucination_count += len(re.findall(pattern, response, re.IGNORECASE))
        
        return {
            "citations_valid": valid,
            "missing_citations": missing,
            "unused_sources": extra,
            "hallucination_risk": "high" if hallucination_count > 2 else "low",
            "source_count": len(sources),
            "cited_source_count": len(set(
                int(n.strip()) - 1 
                for match in re.findall(r'\[(\d+(?:,\s*\d+)*)\]', response)
                for n in match.split(",")
            )),
        }


# =============================================================================
# RETRIEVAL FAILURE HANDLING
# =============================================================================

class RetrievalFailureHandler:
    """Handles retrieval failures gracefully."""
    
    @staticmethod
    def handle_failure(
        error: Exception,
        query: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Handle retrieval failure and return safe fallback response.
        """
        logger.error(f"Retrieval failed for user {user_id}: {error}")
        
        # Classify error type
        error_str = str(error).lower()
        if "timeout" in error_str or "timed out" in error_str:
            return {
                "retrieval_status": "timeout",
                "fallback": "I'm having trouble accessing my memory right now. Could you try rephrasing your question?",
                "retry_suggested": True,
            }
        elif "connection" in error_str or "unavailable" in error_str:
            return {
                "retrieval_status": "unavailable",
                "fallback": "My memory system is temporarily unavailable. I can still help based on our current conversation.",
                "retry_suggested": True,
            }
        elif "dimension" in error_str or "embedding" in error_str:
            return {
                "retrieval_status": "configuration_error",
                "fallback": "There's a configuration issue with my memory system. Please contact support.",
                "retry_suggested": False,
            }
        else:
            return {
                "retrieval_status": "error",
                "fallback": "I encountered an issue retrieving relevant information. I'll do my best to help without it.",
                "retry_suggested": True,
            }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Path mapping
    "RetrievalPath",
    "ActiveRetrievalConfig",
    "get_active_retrieval_config",
    "describe_retrieval_path",
    
    # Ingestion
    "IngestionSecurityError",
    "IngestionValidator",
    "DocumentProcessor",
    "ChunkingConfig",
    "DocumentChunk",
    "DocumentChunker",
    
    # Evaluation
    "RetrievalMetrics",
    "RetrievalEvaluator",
    
    # Grounding
    "GroundedGenerator",
    
    # Failure handling
    "RetrievalFailureHandler",
    
    # Config
    "describe_retrieval_path",
    "get_active_retrieval_config",
]