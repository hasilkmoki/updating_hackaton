"""Government Extractor"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor


class GovernmentExtractor(BaseExtractor):
    def extract(self, text: str, metadata: dict = None) -> dict:
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract application ID
        app_match = re.search(r'(?:application|APP)[:\s#]+([A-Z0-9\-]+)', text, re.IGNORECASE)
        if app_match:
            events.append({
                "event_id": self.generate_event_id("app"),
                "type": "application",
                "app_id": app_match.group(1),
                "status": "submitted",
                "deadline": self._extract_deadline(text),
                "confidence": 0.9,
                "provenance": [self.create_provenance(file_id, snippet=text[:200])]
            })
        
        return {"events": events}
    
    def _extract_deadline(self, text: str) -> str:
        deadline_match = re.search(r'(?:deadline|due|expires)[:\s]+(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
        return deadline_match.group(1) if deadline_match else None

