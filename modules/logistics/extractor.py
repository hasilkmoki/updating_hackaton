"""
Logistics Sector Extractor
Comprehensive extraction: shipments, GPS, temperature, delivery status, delays
"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor


class LogisticsExtractor(BaseExtractor):
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract logistics events - comprehensive tracking"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract shipment information
        events.extend(self._extract_shipments(text, file_id))
        
        # Extract GPS coordinates
        events.extend(self._extract_gps(text, file_id))
        
        # Extract temperature (for cold chain)
        events.extend(self._extract_temperature(text, file_id))
        
        # Extract delivery status
        events.extend(self._extract_delivery_status(text, file_id))
        
        # Extract timestamps and ETAs
        events.extend(self._extract_timestamps(text, file_id))
        
        return {"events": events}
    
    def _extract_shipments(self, text: str, file_id: str) -> List[Dict]:
        """Extract shipment information"""
        events = []
        patterns = [
            r'(?:shipment|SHP|tracking)[:\s#]+([A-Z0-9\-]+)',
            r'AWB[:\s]+([A-Z0-9]+)',
            r'Tracking\s*ID[:\s]+([A-Z0-9\-]+)',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("ship"),
                    "type": "shipment",
                    "shipment_id": match.group(1),
                    "status": self._extract_status(text),
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.9,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_gps(self, text: str, file_id: str) -> List[Dict]:
        """Extract GPS coordinates"""
        events = []
        patterns = [
            r'([0-9]{1,2}\.[0-9]+),\s*([0-9]{1,3}\.[0-9]+)',  # lat,lon
            r'Lat[:\s]+([0-9.]+)[,\s]+Lon[:\s]+([0-9.]+)',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                lat = float(match.group(1))
                lon = float(match.group(2))
                # Validate GPS coordinates
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                    events.append({
                        "event_id": self.generate_event_id("gps"),
                        "type": "gps",
                        "lat": lat,
                        "lon": lon,
                        "date": self._extract_date_near_match(text, match.start()),
                        "confidence": 0.8,
                        "provenance": [self.create_provenance(file_id, snippet=snippet)]
                    })
        return events
    
    def _extract_temperature(self, text: str, file_id: str) -> List[Dict]:
        """Extract temperature readings (for cold chain)"""
        events = []
        pattern = r'(?:temp|temperature)[:\s]+([0-9.+-]+)\s*[°C]?'
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
    
    def _extract_delivery_status(self, text: str, file_id: str) -> List[Dict]:
        """Extract delivery status"""
        events = []
        status_keywords = {
            "delivered": r'\bdelivered\b',
            "in-transit": r'\b(?:in.?transit|shipped|dispatched)\b',
            "out-for-delivery": r'\b(?:out\s*for\s*delivery|ofd)\b',
            "failed": r'\b(?:failed|undelivered|returned)\b',
        }
        for status, pattern in status_keywords.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("del"),
                    "type": "delivery_status",
                    "status": status,
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_timestamps(self, text: str, file_id: str) -> List[Dict]:
        """Extract timestamps and ETAs"""
        events = []
        patterns = [
            r'ETA[:\s]+(\d{2}[/-]\d{2}[/-]\d{4}\s+\d{2}:\d{2})',
            r'Expected[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("eta"),
                    "type": "eta",
                    "expected_time": match.group(1),
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.8,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_status(self, text: str) -> str:
        """Extract shipment status"""
        text_lower = text.lower()
        if "delivered" in text_lower:
            return "delivered"
        elif "out for delivery" in text_lower or "ofd" in text_lower:
            return "out-for-delivery"
        elif "in transit" in text_lower or "shipped" in text_lower:
            return "in-transit"
        elif "failed" in text_lower or "returned" in text_lower:
            return "failed"
        return "in-transit"
    
    def _extract_date_near_match(self, text: str, position: int) -> str:
        """Extract date near match"""
        start = max(0, position - 100)
        end = min(len(text), position + 100)
        context = text[start:end]
        date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', context)
        return date_match.group(1) if date_match else None

