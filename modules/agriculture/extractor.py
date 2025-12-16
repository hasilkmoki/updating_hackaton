"""
Agriculture Sector Extractor
Extracts soil moisture, NDVI, temperature from agricultural data
"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor


class AgricultureExtractor(BaseExtractor):
    """Extract agriculture events from text"""
    
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract agriculture events"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract soil moisture
        events.extend(self._extract_soil_moisture(text, file_id))
        
        # Extract NDVI
        events.extend(self._extract_ndvi(text, file_id))
        
        # Extract temperature
        events.extend(self._extract_temperature(text, file_id))
        
        return {"events": events}
    
    def _extract_soil_moisture(self, text: str, file_id: str) -> List[Dict]:
        """Extract soil moisture readings"""
        events = []
        pattern = r'(?:soil\s*moisture|moisture)[:\s]+([0-9.]+)\s*%'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1))
            snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
            events.append({
                "event_id": self.generate_event_id("soil"),
                "type": "soil_moisture",
                "value": value,
                "units": "%",
                "date": self._extract_date_near_match(text, match.start()),
                "field_id": self._extract_field_id(text, match.start()),
                "confidence": 0.9,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        return events
    
    def _extract_ndvi(self, text: str, file_id: str) -> List[Dict]:
        """Extract NDVI values"""
        events = []
        pattern = r'NDVI[:\s]+([0-9.]+)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1))
            snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
            events.append({
                "event_id": self.generate_event_id("ndvi"),
                "type": "ndvi",
                "value": value,
                "date": self._extract_date_near_match(text, match.start()),
                "field_id": self._extract_field_id(text, match.start()),
                "confidence": 0.9,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        return events
    
    def _extract_temperature(self, text: str, file_id: str) -> List[Dict]:
        """Extract temperature readings"""
        events = []
        pattern = r'(?:temp|temperature)[:\s]+([0-9.]+)\s*[°C]?'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1))
            snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
            events.append({
                "event_id": self.generate_event_id("temp"),
                "type": "temperature",
                "value": value,
                "units": "C",
                "date": self._extract_date_near_match(text, match.start()),
                "confidence": 0.85,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        return events
    
    def _extract_date_near_match(self, text: str, position: int) -> str:
        """Extract date near match"""
        start = max(0, position - 100)
        end = min(len(text), position + 100)
        context = text[start:end]
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', context)
        return date_match.group(1) if date_match else None
    
    def _extract_field_id(self, text: str, position: int) -> str:
        """Extract field ID"""
        start = max(0, position - 50)
        end = min(len(text), position + 50)
        context = text[start:end]
        field_match = re.search(r'field[:\s]+([0-9]+)', context, re.IGNORECASE)
        return f"field_{field_match.group(1)}" if field_match else "field_unknown"

