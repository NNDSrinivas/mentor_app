"""Knowledge base integration module.

This module provides a real knowledge base implementation using ChromaDB
for vector storage and OpenAI embeddings. It can ingest documents, code files,
and other content, then provide semantic search and retrieval capabilities.
"""
from __future__ import annotations

import logging
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings
from openai import OpenAI

from .config import Config
from .memory_db import MemoryDB

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Vector-based knowledge base using ChromaDB and OpenAI embeddings."""
    
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for knowledge base")
        
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection("knowledge_base")
            logger.info("Loaded existing knowledge base collection")
        except:
            self.collection = self.chroma_client.create_collection(
                name="knowledge_base",
                metadata={"description": "AI Mentor Assistant Knowledge Base"}
            )
            logger.info("Created new knowledge base collection")

        # Initialize persistence layer for summaries and tasks
        self.db = MemoryDB()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI API.
        
        Args:
            text: Text to embed.
            
        Returns:
            Embedding vector.
        """
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=Config.EMBEDDING_MODEL
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add a document to the knowledge base.
        
        Args:
            content: Document content.
            metadata: Document metadata (title, source, type, etc.).
            
        Returns:
            Document ID.
        """
        try:
            # Generate document ID
            doc_id = hashlib.md5(content.encode()).hexdigest()
            
            # Add timestamp to metadata
            metadata["timestamp"] = datetime.now().isoformat()
            metadata["content_length"] = len(content)
            
            # Generate embedding
            embedding = self.generate_embedding(content)
            
            # Add to collection
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                embeddings=[embedding],
                ids=[doc_id]
            )
            
            logger.info(f"Added document to knowledge base: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add document: {str(e)}")
            raise
    
    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search the knowledge base.
        
        Args:
            query: Search query.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filters.
            
        Returns:
            List of search results.
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity_score": 1 - results["distances"][0][i],  # Convert distance to similarity
                    "id": results["ids"][0][i] if "ids" in results else None
                })
            
            logger.info(f"Knowledge base search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Knowledge base search failed: {str(e)}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the knowledge base collection.
        
        Returns:
            Collection statistics.
        """
        try:
            count = self.collection.count()
            return {
                "document_count": count,
                "collection_name": self.collection.name,
                "persist_directory": Config.CHROMA_PERSIST_DIR
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            return {"error": str(e)}
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the knowledge base.
        
        Args:
            doc_id: Document ID to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            return False

    # --- Persistence helpers ---
    def save_meeting_summary(self, meeting_id: str, summary: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Persist a meeting summary and add it to the vector store."""
        self.db.save_meeting_summary(meeting_id, summary)
        meta = {"type": "meeting_summary", "meeting_id": meeting_id, **(metadata or {})}
        return self.add_document(summary, meta)

    def get_meeting_summaries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent meeting summaries from persistence."""
        return self.db.get_meeting_summaries(limit)

    def save_task_history(self, task_id: str, description: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Persist a task entry and add it to the vector store."""
        self.db.save_task(task_id, description)
        meta = {"type": "task", "task_id": task_id, **(metadata or {})}
        return self.add_document(description, meta)

    def get_task_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent task history from persistence."""
        return self.db.get_task_history(limit)


def ingest_documents(docs: List[str], doc_type: str = "general") -> None:
    """Ingest a list of documents into the knowledge base.

    Args:
        docs: A list of strings representing documents to ingest.
        doc_type: Type of documents being ingested.
    """
    logger.info("Ingesting %d documents into knowledge base", len(docs))
    
    if not docs:
        logger.warning("No documents provided for ingestion")
        return
    
    try:
        kb = KnowledgeBase()
        
        for i, doc in enumerate(docs):
            if not doc.strip():
                continue
                
            metadata = {
                "type": doc_type,
                "source": "manual_ingestion",
                "index": i,
                "title": f"{doc_type}_document_{i}"
            }
            
            kb.add_document(doc, metadata)
        
        logger.info(f"Successfully ingested {len(docs)} documents")
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {str(e)}")


def ingest_file(file_path: str, doc_type: str = "file") -> str:
    """Ingest a single file into the knowledge base.
    
    Args:
        file_path: Path to the file to ingest.
        doc_type: Type of document.
        
    Returns:
        Document ID if successful, error message otherwise.
    """
    logger.info(f"Ingesting file: {file_path}")
    
    if not os.path.exists(file_path):
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        return error_msg
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        kb = KnowledgeBase()
        metadata = {
            "type": doc_type,
            "source": "file",
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path)
        }
        
        doc_id = kb.add_document(content, metadata)
        logger.info(f"Successfully ingested file {file_path} as {doc_id}")
        return doc_id
        
    except Exception as e:
        error_msg = f"Failed to ingest file {file_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg


def ingest_code_repository(repo_path: str) -> Dict[str, Any]:
    """Ingest code files from a repository.
    
    Args:
        repo_path: Path to the code repository.
        
    Returns:
        Ingestion results.
    """
    logger.info(f"Ingesting code repository: {repo_path}")
    
    if not os.path.exists(repo_path):
        return {"error": f"Repository path not found: {repo_path}"}
    
    # Code file extensions to process
    code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.rb', '.go', '.rs', '.php'}
    
    ingested_files = []
    failed_files = []
    
    try:
        kb = KnowledgeBase()
        
        for root, dirs, files in os.walk(repo_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                
                if ext.lower() in code_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        metadata = {
                            "type": "code",
                            "source": "repository",
                            "file_path": file_path,
                            "filename": file,
                            "extension": ext,
                            "relative_path": os.path.relpath(file_path, repo_path)
                        }
                        
                        doc_id = kb.add_document(content, metadata)
                        ingested_files.append({"file": file_path, "doc_id": doc_id})
                        
                    except Exception as e:
                        failed_files.append({"file": file_path, "error": str(e)})
                        logger.warning(f"Failed to ingest {file_path}: {str(e)}")
        
        result = {
            "repository_path": repo_path,
            "ingested_count": len(ingested_files),
            "failed_count": len(failed_files),
            "ingested_files": ingested_files,
            "failed_files": failed_files
        }
        
        logger.info(f"Repository ingestion completed: {len(ingested_files)} files ingested, {len(failed_files)} failed")
        return result
        
    except Exception as e:
        error_msg = f"Repository ingestion failed: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def query_knowledge_base(query: str, top_k: int = 3, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query the knowledge base for relevant documents.

    Args:
        query: Natural language query.
        top_k: Number of documents to retrieve.
        doc_type: Optional filter by document type.

    Returns:
        A list of document metadata and content.
    """
    logger.info("Querying knowledge base: %s", query)
    
    if not query.strip():
        logger.warning("Empty query provided")
        return []
    
    try:
        kb = KnowledgeBase()
        
        # Build filter if doc_type specified
        filter_metadata = {"type": doc_type} if doc_type else None
        
        results = kb.search(query, top_k, filter_metadata)
        
        logger.info(f"Knowledge base query returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Knowledge base query failed: {str(e)}")
        return [{"error": str(e)}]


def get_knowledge_base_stats() -> Dict[str, Any]:
    """Get knowledge base statistics.
    
    Returns:
        Statistics about the knowledge base.
    """
    try:
        kb = KnowledgeBase()
        return kb.get_collection_info()
        
    except Exception as e:
        logger.error(f"Failed to get knowledge base stats: {str(e)}")
        return {"error": str(e)}


def search_code(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search specifically for code content.
    
    Args:
        query: Search query for code.
        top_k: Number of results to return.
        
    Returns:
        List of matching code snippets.
    """
    logger.info(f"Searching code with query: {query}")
    
    return query_knowledge_base(query, top_k, "code")
