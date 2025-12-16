"""
STEP 8 — CHATBOT (RAG-based Q&A)
Uses vector DB and LLM to answer questions
"""
import os
from dotenv import load_dotenv
from step5_core_reasoner import CoreReasoner

try:
    from groq import Groq
except Exception:
    Groq = None  # Optional dependency for LLM answers

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"
client = None
if GROQ_API_KEY and Groq is not None:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Groq init error, chatbot will answer without LLM: {e}")


class Chatbot:
    """RAG-based chatbot"""
    
    def __init__(self, core_reasoner: CoreReasoner):
        self.core_reasoner = core_reasoner
    
    def answer_query(self, entity_id: str, query: str, top_k: int = 6) -> dict:
        """
        Answer user query using RAG
        
        Returns:
        {
            "answer": "...",
            "sources": [...]
        }
        """
        # Search vector DB
        chunks = self.core_reasoner.search_vector_db(query, entity_id, top_k)
        
        # Build context with readable separators
        context_text = "\n\n".join([c.get("text", "") for c in chunks])
        
        # Get timeline for additional context
        timeline = self.core_reasoner.get_timeline(entity_id, limit=10)
        timeline_text = "\n".join([f"{e.get('type')}: {str(e)[:100]}" for e in timeline[:5]])
        
        # Build prompt
        prompt = f"""You are a helpful assistant answering questions about documents and data.

Context from documents:
{context_text}

Recent timeline:
{timeline_text}

User question: {query}

Provide a clear, concise answer based on the context above. If the information is not available, say so."""

        if client is None:
            # Fallback: answer from available context without LLM
            fallback_answer = "No LLM available. "
            if context_text.strip() or timeline_text.strip():
                fallback_answer += "Here is what I can see:\n" + (context_text[:500] or timeline_text[:500])
            else:
                fallback_answer += "No context found for this entity."
            return {
                "answer": fallback_answer,
                "sources": [
                    {
                        "text": c.get("text", "")[:200],
                        "file_id": c.get("metadata", {}).get("file_id"),
                        "relevance": 1 - (c.get("distance", 1) if c.get("distance") else 1)
                    }
                    for c in chunks
                ]
            }

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful document analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "sources": [
                    {
                        "text": c.get("text", "")[:200],
                        "file_id": c.get("metadata", {}).get("file_id"),
                        "relevance": 1 - (c.get("distance", 1) if c.get("distance") else 1)
                    }
                    for c in chunks
                ]
            }
        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": []
            }
