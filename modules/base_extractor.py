"""
Base extractor class for all sector modules
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import uuid


class BaseExtractor(ABC):
    """Base class for sector-specific extractors"""
    
    @abstractmethod
    def extract(self, text: str, metadata: dict = None) -> dict:
        """
        Extract structured events from text
        
        Returns:
        {
            "events": [
                {
                    "event_id": "ev1",
                    "type": "...",
                    ...
                    "confidence": 0.94,
                    "provenance": [...]
                }
            ]
        }
        """
        pass
    
    def generate_event_id(self, prefix: str = "ev") -> str:
        """Generate unique event ID"""
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    def create_provenance(self, file_id: str, page: int = None, snippet: str = None, offset: int = None) -> dict:
        """Create provenance record"""
        prov = {"file_id": file_id}
        if page:
            prov["page"] = page
        if snippet:
            prov["snippet"] = snippet[:200]  # Limit snippet length
        if offset:
            prov["offset"] = offset
        return prov

