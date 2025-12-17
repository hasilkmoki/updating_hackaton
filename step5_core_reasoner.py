"""
STEP 5 — CORE REASONER (Universal Brain)
Organizes information: timeline, vector DB, knowledge graph
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Enable FAISS-based vector DB
USE_VECTOR_DB = True

# Database setup
DB_DIR = Path("storage/db")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "events.db"


class CoreReasoner:
    """Core reasoner for organizing and storing information"""
    
    def __init__(self):
        # Vector DB members
        self.embedding_model: Optional[SentenceTransformer] = None
        self.faiss_index: Optional[faiss.IndexFlatIP] = None
        self.faiss_ids: list[str] = []              # index -> chunk_id
        self.faiss_metadata: Dict[str, Dict] = {}   # chunk_id -> metadata
        self.faiss_texts: Dict[str, str] = {}       # chunk_id -> raw chunk text (kept in-memory for chatbot context)

        self._init_db()
        self._init_vector_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                entity_id TEXT,
                event_type TEXT,
                event_data TEXT,
                date TEXT,
                source_file TEXT,
                stored_at TEXT,
                sector TEXT
            )
        """)
        
        # Timeline table (for quick access)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeline (
                entity_id TEXT,
                event_id TEXT,
                date TEXT,
                event_type TEXT,
                PRIMARY KEY (entity_id, event_id)
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                entity_id TEXT,
                title TEXT,
                severity TEXT,
                reason TEXT,
                source_file TEXT,
                evidence TEXT,
                recommended_actions TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_entity ON alerts(entity_id, status)
        """)
        
        conn.commit()
        conn.close()
    
    def _init_vector_db(self):
        """Initialize FAISS + sentence-transformers vector database"""
        if not USE_VECTOR_DB:
            print("Vector DB disabled. Chatbot will answer without RAG context.")
            return

        try:
            # Use a lightweight, general-purpose model
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            dim = self.embedding_model.get_sentence_embedding_dimension()

            # Cosine similarity via inner product on normalized vectors
            self.faiss_index = faiss.IndexFlatIP(dim)
            self.faiss_ids = []
            self.faiss_metadata = {}
            self.faiss_texts = {}

            print(f"Vector DB initialized with FAISS (dimension={dim})")
        except Exception as e:
            print(f"Vector DB init error: {e}")
            self.embedding_model = None
            self.faiss_index = None
            self.faiss_ids = []
            self.faiss_metadata = {}
    
    def store_events(self, events: List[Dict], entity_id: str, file_id: str, sector: str) -> dict:
        """
        Store events in database and update timeline
        
        Returns:
        {
            "timeline_updated": true,
            "events_stored": [...]
        }
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        stored_events = []
        
        for event in events:
            event_id = event.get("event_id", f"ev_{datetime.now().timestamp()}")
            event_type = event.get("type", "unknown")
            event_date = event.get("date") or datetime.now().isoformat()
            
            # Store event
            cursor.execute("""
                INSERT OR REPLACE INTO events 
                (id, entity_id, event_type, event_data, date, source_file, stored_at, sector)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                entity_id,
                event_type,
                json.dumps(event),
                event_date,
                file_id,
                datetime.now().isoformat(),
                sector
            ))
            
            # Update timeline
            cursor.execute("""
                INSERT OR REPLACE INTO timeline (entity_id, event_id, date, event_type)
                VALUES (?, ?, ?, ?)
            """, (entity_id, event_id, event_date, event_type))
            
            stored_events.append(event_id)
        
        conn.commit()
        conn.close()
        
        return {
            "timeline_updated": True,
            "events_stored": stored_events
        }
    
    def create_embeddings(self, events: List[Dict], file_id: str, entity_id: str, text: str):
        """
        Create embeddings and store in vector DB
        Uses sentence-transformers + FAISS.
        """
        if not USE_VECTOR_DB or self.embedding_model is None or self.faiss_index is None:
            return {"vector_db_updated": False, "reason": "Vector DB not available"}

        # Chunk text (simple 500 char chunks)
        chunk_size = 500
        chunks: list[Dict[str, Any]] = []
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i : i + chunk_size]
            if not chunk_text.strip():
                continue
            chunk_id = f"{file_id}_chunk_{i // chunk_size}"
            chunks.append(
                {
                    "text": chunk_text,
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "entity_id": entity_id,
                }
            )

        if not chunks:
            return {"vector_db_updated": False, "reason": "No text chunks to index"}

        try:
            texts = [c["text"] for c in chunks]
            # Compute embeddings and normalize for cosine similarity
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            embeddings = embeddings.astype("float32")
            faiss.normalize_L2(embeddings)

            # Add to FAISS index
            self.faiss_index.add(embeddings)

            # Store IDs, metadata, and raw text for chatbot context
            for c in chunks:
                self.faiss_ids.append(c["chunk_id"])
                self.faiss_metadata[c["chunk_id"]] = {
                    "file_id": c["file_id"],
                    "entity_id": c["entity_id"],
                }
                self.faiss_texts[c["chunk_id"]] = c["text"]

            return {
                "vector_db_updated": True,
                "chunks_stored": len(chunks),
            }
        except Exception as e:
            print(f"Vector DB error: {e}")
            return {"vector_db_updated": False, "error": str(e)}
    
    def get_timeline(self, entity_id: str, limit: int = 100) -> List[Dict]:
        """Get timeline for entity"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.event_data, e.date, e.event_type
            FROM events e
            WHERE e.entity_id = ?
            ORDER BY e.date DESC
            LIMIT ?
        """, (entity_id, limit))
        
        timeline = []
        for row in cursor.fetchall():
            event_data = json.loads(row[0])
            timeline.append({
                **event_data,
                "date": row[1],
                "type": row[2]
            })
        
        conn.close()
        return timeline
    
    def search_vector_db(self, query: str, entity_id: str, top_k: int = 6) -> List[Dict]:
        """Search FAISS vector database, filtered by entity_id"""
        if (
            not USE_VECTOR_DB
            or self.embedding_model is None
            or self.faiss_index is None
            or len(self.faiss_ids) == 0
        ):
            return []

        if not query.strip():
            return []

        try:
            # Embed query
            q_emb = self.embedding_model.encode([query], convert_to_numpy=True, show_progress_bar=False)
            q_emb = q_emb.astype("float32")
            faiss.normalize_L2(q_emb)

            # Search in FAISS
            # n_search = min(len(self.faiss_ids), max(top_k * 3, top_k))
            n_search = min(len(self.faiss_ids), max(top_k * 3, top_k))
            scores, idxs = self.faiss_index.search(q_emb, n_search)

            hits: List[Dict] = []
            for score, idx in zip(scores[0], idxs[0]):
                if idx < 0 or idx >= len(self.faiss_ids):
                    continue
                chunk_id = self.faiss_ids[idx]
                meta = self.faiss_metadata.get(chunk_id, {})
                if entity_id and meta.get("entity_id") != entity_id:
                    continue

                # Reconstruct text from stored info is not persisted; we don't keep full text per chunk here.
                # For now, we return only metadata and score. Chatbot will mostly use timeline + alerts.
                hits.append(
                    {
                        "text": self.faiss_texts.get(chunk_id, ""),
                        "metadata": meta,
                        "distance": float(1.0 - score),  # convert similarity to pseudo-distance
                    }
                )

                if len(hits) >= top_k:
                    break

            return hits
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    def store_alerts(self, alerts: List[Dict], entity_id: str) -> dict:
        """
        Store alerts in database
        
        Returns:
        {
            "alerts_stored": [...]
        }
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        stored_alert_ids = []
        
        for alert in alerts:
            alert_id = alert.get("alert_id")
            if not alert_id:
                continue
                
            cursor.execute("""
                INSERT OR REPLACE INTO alerts 
                (alert_id, entity_id, title, severity, reason, source_file, 
                 evidence, recommended_actions, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_id,
                entity_id,
                alert.get("title", ""),
                alert.get("severity", "medium"),
                alert.get("reason", ""),
                alert.get("source_file", ""),
                json.dumps(alert.get("evidence", [])),
                json.dumps(alert.get("recommended_actions", [])),
                alert.get("created_at", datetime.now().isoformat()),
                "active"
            ))
            
            stored_alert_ids.append(alert_id)
        
        conn.commit()
        conn.close()
        
        return {
            "alerts_stored": stored_alert_ids
        }
    
    def get_alerts(self, entity_id: str, status: str = "active", limit: int = 100) -> List[Dict]:
        """Get alerts for entity"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT alert_id, title, severity, reason, source_file, 
                   evidence, recommended_actions, created_at, status
            FROM alerts
            WHERE entity_id = ? AND status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (entity_id, status, limit))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                "alert_id": row[0],
                "title": row[1],
                "severity": row[2],
                "reason": row[3],
                "source_file": row[4],
                "evidence": json.loads(row[5]) if row[5] else [],
                "recommended_actions": json.loads(row[6]) if row[6] else [],
                "created_at": row[7],
                "status": row[8]
            })
        
        conn.close()
        return alerts

