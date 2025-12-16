"""Logistics Extractor"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor


class LogisticsExtractor(BaseExtractor):
    def extract(self, text: str, metadata: dict = None) -> dict:
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract shipment ID
        shipment_match = re.search(r'(?:shipment|SHP)[:\s#]+([A-Z0-9\-]+)', text, re.IGNORECASE)
        if shipment_match:
            events.append({
                "event_id": self.generate_event_id("ship"),
                "type": "shipment",
                "shipment_id": shipment_match.group(1),
                "status": "in-transit",
                "confidence": 0.9,
                "provenance": [self.create_provenance(file_id, snippet=text[:200])]
            })
        
        # Extract GPS
        gps_match = re.search(r'([0-9.]+),\s*([0-9.]+)', text)
        if gps_match:
            events.append({
                "event_id": self.generate_event_id("gps"),
                "type": "gps",
                "lat": float(gps_match.group(1)),
                "lon": float(gps_match.group(2)),
                "confidence": 0.8,
                "provenance": [self.create_provenance(file_id, snippet=text[:200])]
            })
        
        return {"events": events}

