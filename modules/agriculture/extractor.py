"""
Agriculture Sector Extractor
Comprehensive extraction: soil moisture, NDVI, temperature, 
rainfall, crop health, irrigation, pest data
"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor
from modules.llm_extractor import LLMExtractor


class AgricultureExtractor(BaseExtractor):
    """Extract agriculture events from text"""
    
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract agriculture events - comprehensive sensor and crop data"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract sensor data
        events.extend(self._extract_soil_moisture(text, file_id))
        events.extend(self._extract_ndvi(text, file_id))
        events.extend(self._extract_temperature(text, file_id))
        events.extend(self._extract_rainfall(text, file_id))
        events.extend(self._extract_ph(text, file_id))
        events.extend(self._extract_nutrients(text, file_id))
        
        # Extract crop events
        events.extend(self._extract_irrigation(text, file_id))
        events.extend(self._extract_pest_disease(text, file_id))
        events.extend(self._extract_harvest(text, file_id))
        
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
        field_match = re.search(r'field[:\s]+([0-9A-Z]+)', context, re.IGNORECASE)
        return f"field_{field_match.group(1)}" if field_match else "field_unknown"
    
    def _extract_rainfall(self, text: str, file_id: str) -> List[Dict]:
        """Extract rainfall data"""
        events = []
        patterns = [
            r'(?:rainfall|rain|precipitation)[:\s]+([0-9.]+)\s*(?:mm|cm)?',
            r'([0-9.]+)\s*mm\s*(?:rain|rainfall)',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = float(match.group(1))
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("rain"),
                    "type": "rainfall",
                    "value": value,
                    "units": "mm",
                    "date": self._extract_date_near_match(text, match.start()),
                    "field_id": self._extract_field_id(text, match.start()),
                    "confidence": 0.9,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_ph(self, text: str, file_id: str) -> List[Dict]:
        """Extract soil pH values"""
        events = []
        pattern = r'(?:pH|ph)[:\s]+([0-9.]+)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1))
            snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
            events.append({
                "event_id": self.generate_event_id("ph"),
                "type": "soil_ph",
                "value": value,
                "units": "pH",
                "date": self._extract_date_near_match(text, match.start()),
                "field_id": self._extract_field_id(text, match.start()),
                "confidence": 0.9,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        return events
    
    def _extract_nutrients(self, text: str, file_id: str) -> List[Dict]:
        """Extract nutrient levels (N, P, K)"""
        events = []
        nutrients = {
            'nitrogen': r'(?:nitrogen|N)[:\s]+([0-9.]+)',
            'phosphorus': r'(?:phosphorus|P)[:\s]+([0-9.]+)',
            'potassium': r'(?:potassium|K)[:\s]+([0-9.]+)',
        }
        for nutrient, pattern in nutrients.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = float(match.group(1))
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("nut"),
                    "type": f"nutrient_{nutrient}",
                    "nutrient": nutrient,
                    "value": value,
                    "units": "ppm",
                    "date": self._extract_date_near_match(text, match.start()),
                    "field_id": self._extract_field_id(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_irrigation(self, text: str, file_id: str) -> List[Dict]:
        """Extract irrigation events"""
        events = []
        pattern = r'(?:irrigation|irrigated|watered)[:\s]+([0-9.]+)\s*(?:mm|liters?|L)?'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1))
            snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
            events.append({
                "event_id": self.generate_event_id("irr"),
                "type": "irrigation",
                "value": value,
                "units": "mm",
                "date": self._extract_date_near_match(text, match.start()),
                "field_id": self._extract_field_id(text, match.start()),
                "confidence": 0.85,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        return events
    
    def _extract_pest_disease(self, text: str, file_id: str) -> List[Dict]:
        """Extract pest and disease information"""
        events = []
        pests = ['aphid', 'locust', 'caterpillar', 'mite', 'thrips']
        diseases = ['rust', 'blight', 'wilt', 'mosaic', 'rot']
        
        for pest in pests:
            pattern = rf'\b{pest}\b'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("pest"),
                    "type": "pest_detection",
                    "pest": pest,
                    "date": self._extract_date_near_match(text, match.start()),
                    "field_id": self._extract_field_id(text, match.start()),
                    "confidence": 0.8,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        
        for disease in diseases:
            pattern = rf'\b{disease}\b'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("dis"),
                    "type": "disease_detection",
                    "disease": disease,
                    "date": self._extract_date_near_match(text, match.start()),
                    "field_id": self._extract_field_id(text, match.start()),
                    "confidence": 0.8,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        
        return events
    
    def _extract_harvest(self, text: str, file_id: str) -> List[Dict]:
        """Extract harvest information"""
        events = []
        pattern = r'(?:harvest|yield)[:\s]+([0-9.]+)\s*(?:kg|tons?|quintals?)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1))
            snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
            events.append({
                "event_id": self.generate_event_id("har"),
                "type": "harvest",
                "value": value,
                "units": "kg",
                "date": self._extract_date_near_match(text, match.start()),
                "field_id": self._extract_field_id(text, match.start()),
                "confidence": 0.85,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        return events

