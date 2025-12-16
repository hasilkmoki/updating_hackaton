"""
Healthcare Sector Extractor
Extracts labs, meds, diagnoses from medical documents
"""
import re
from typing import Dict, List, Any
from modules.base_extractor import BaseExtractor


class HealthcareExtractor(BaseExtractor):
    """Extract healthcare events from text"""
    
    # Common lab patterns
    LAB_PATTERNS = {
        'hba1c': r'(?:HbA1c|Hb\s*A1c|Hemoglobin\s*A1c)[:\s]+([0-9.]+)\s*%?',
        'glucose': r'(?:Glucose|Blood\s*Sugar|BS)[:\s]+([0-9.]+)\s*(?:mg/dl|mmol/l)?',
        'cholesterol': r'(?:Cholesterol|Total\s*Chol)[:\s]+([0-9.]+)',
        'bp': r'(?:BP|Blood\s*Pressure)[:\s]+([0-9]+)\s*/\s*([0-9]+)',
    }
    
    # Reference ranges
    REF_RANGES = {
        'hba1c': {'min': 4.0, 'max': 6.0},
        'glucose': {'min': 70, 'max': 100},  # mg/dl
        'cholesterol': {'min': 0, 'max': 200},
    }
    
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract healthcare events"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract lab results
        events.extend(self._extract_lab_results(text, file_id))
        
        # Extract medications
        events.extend(self._extract_medications(text, file_id))
        
        # Extract diagnoses
        events.extend(self._extract_diagnoses(text, file_id))
        
        return {
            "events": events
        }
    
    def _extract_lab_results(self, text: str, file_id: str) -> List[Dict]:
        """Extract lab test results"""
        events = []
        text_lower = text.lower()
        
        for test_name, pattern in self.LAB_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value_str = match.group(1)
                try:
                    value = float(value_str)
                    
                    # Get reference range
                    ref_range = self.REF_RANGES.get(test_name, {})
                    
                    # Find snippet
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    snippet = text[start:end]
                    
                    event = {
                        "event_id": self.generate_event_id("lab"),
                        "type": "lab_result",
                        "test": test_name.upper(),
                        "value": value,
                        "units": "%" if test_name == "hba1c" else "mg/dl",
                        "ref_range": f"{ref_range.get('min', 'N/A')}-{ref_range.get('max', 'N/A')}",
                        "date": self._extract_date_near_match(text, match.start()),
                        "confidence": 0.9,
                        "provenance": [self.create_provenance(file_id, snippet=snippet)]
                    }
                    
                    # Check if abnormal
                    if ref_range:
                        if value < ref_range.get('min', 0) or value > ref_range.get('max', 999):
                            event["abnormal"] = True
                    
                    events.append(event)
                except ValueError:
                    continue
        
        return events
    
    def _extract_medications(self, text: str, file_id: str) -> List[Dict]:
        """Extract medication information"""
        events = []
        
        # Common medication patterns
        med_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+)\s*(?:mg|g|ml)',
            r'Prescribed:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        med_keywords = ['metformin', 'insulin', 'aspirin', 'atorvastatin', 'amlodipine']
        
        for keyword in med_keywords:
            pattern = rf'\b{keyword}\b[:\s]+([0-9.]+)\s*(?:mg|g|ml)?'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dose = match.group(1) if match.lastindex else "unknown"
                
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                snippet = text[start:end]
                
                events.append({
                    "event_id": self.generate_event_id("med"),
                    "type": "medication",
                    "name": keyword.capitalize(),
                    "dose": f"{dose} mg",
                    "frequency": self._extract_frequency(text, match.start()),
                    "start_date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        
        return events
    
    def _extract_diagnoses(self, text: str, file_id: str) -> List[Dict]:
        """Extract diagnoses"""
        events = []
        
        diagnosis_keywords = ['diabetes', 'hypertension', 'asthma', 'copd', 'anemia']
        
        for keyword in diagnosis_keywords:
            pattern = rf'\b{keyword}\b'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                snippet = text[start:end]
                
                events.append({
                    "event_id": self.generate_event_id("diag"),
                    "type": "diagnosis",
                    "condition": keyword.capitalize(),
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.8,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        
        return events
    
    def _extract_date_near_match(self, text: str, position: int) -> str:
        """Extract date near match position"""
        # Look for date patterns within 100 chars
        start = max(0, position - 100)
        end = min(len(text), position + 100)
        context = text[start:end]
        
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_frequency(self, text: str, position: int) -> str:
        """Extract medication frequency"""
        start = max(0, position - 50)
        end = min(len(text), position + 50)
        context = text[start:end].lower()
        
        if 'twice' in context or '2x' in context:
            return "2x/day"
        elif 'once' in context or '1x' in context:
            return "1x/day"
        elif 'three' in context or '3x' in context:
            return "3x/day"
        
        return "as prescribed"

