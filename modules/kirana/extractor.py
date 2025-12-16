"""Kirana Shop Extractor"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor


class KiranaExtractor(BaseExtractor):
    def extract(self, text: str, metadata: dict = None) -> dict:
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract bill
        bill_match = re.search(r'(?:bill|BILL)[\s#:]+([A-Z0-9\-]+)', text, re.IGNORECASE)
        if bill_match:
            events.append({
                "event_id": self.generate_event_id("bill"),
                "type": "bill",
                "bill_no": bill_match.group(1),
                "vendor": self._extract_vendor(text),
                "amount": self._extract_amount(text),
                "date": self._extract_date(text),
                "paid": "paid" in text.lower(),
                "confidence": 0.85,
                "provenance": [self.create_provenance(file_id, snippet=text[:200])]
            })
        
        return {"events": events}
    
    def _extract_vendor(self, text: str) -> str:
        match = re.search(r'(?:from|vendor)[:\s]+([A-Z][A-Za-z\s]+)', text, re.IGNORECASE)
        return match.group(1).strip() if match else "Unknown"
    
    def _extract_amount(self, text: str) -> float:
        match = re.search(r'[₹Rs]\s*([\d,]+\.?\d*)', text)
        return float(match.group(1).replace(",", "")) if match else 0.0
    
    def _extract_date(self, text: str) -> str:
        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        return match.group(1) if match else None

