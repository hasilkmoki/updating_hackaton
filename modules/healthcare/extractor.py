"""
Healthcare Sector Extractor
Extracts labs, meds, diagnoses from medical documents
Uses regex patterns + LLM fallback for comprehensive extraction
"""
import re
from typing import Dict, List, Any
from modules.base_extractor import BaseExtractor
from modules.llm_extractor import LLMExtractor


class HealthcareExtractor(BaseExtractor):
    """Extract healthcare events from text"""
    
    # Common lab patterns - extended for more tests
    LAB_PATTERNS = {
        'hba1c': r'(?:HbA1c|Hb\s*A1c|Hemoglobin\s*A1c)[:\s]+([0-9.]+)\s*%?',
        'glucose': r'(?:Glucose|Blood\s*Sugar|BS|FBS|Fasting)[:\s]+([0-9.]+)\s*(?:mg/dl|mmol/l)?',
        'cholesterol': r'(?:Cholesterol|Total\s*Chol|CHOL)[:\s]+([0-9.]+)',
        'bp': r'(?:BP|Blood\s*Pressure)[:\s]+([0-9]+)\s*/\s*([0-9]+)',
        'hemoglobin': r'(?:Hemoglobin|Hgb|Hb)[:\s]+([0-9.]+)\s*(?:g/dl|g/dL)?',
        'creatinine': r'(?:Creatinine|CREAT)[:\s]+([0-9.]+)\s*(?:mg/dl)?',
        'tsh': r'(?:TSH|Thyroid\s*Stimulating)[:\s]+([0-9.]+)',
        'alt': r'(?:ALT|SGPT)[:\s]+([0-9.]+)',
        'ast': r'(?:AST|SGOT)[:\s]+([0-9.]+)',
        'ldl': r'(?:LDL)[:\s]+([0-9.]+)',
        'hdl': r'(?:HDL)[:\s]+([0-9.]+)',
    }
    
    # Reference ranges - extended
    REF_RANGES = {
        'hba1c': {'min': 4.0, 'max': 6.0},
        'glucose': {'min': 70, 'max': 100},  # mg/dl
        'cholesterol': {'min': 0, 'max': 200},
        'hemoglobin': {'min': 12.0, 'max': 16.0},  # g/dl for women, 14-18 for men (using average)
        'creatinine': {'min': 0.6, 'max': 1.2},  # mg/dl
        'tsh': {'min': 0.4, 'max': 4.0},  # mIU/L
        'alt': {'min': 7, 'max': 56},  # U/L
        'ast': {'min': 10, 'max': 40},  # U/L
        'ldl': {'min': 0, 'max': 100},  # mg/dl (optimal)
        'hdl': {'min': 40, 'max': 200},  # mg/dl (higher is better)
    }
    
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract healthcare events - regex first, LLM fallback for complex cases"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Primary extraction using regex patterns (fast and accurate for structured data)
        events.extend(self._extract_lab_results(text, file_id))
        events.extend(self._extract_medications(text, file_id))
        events.extend(self._extract_diagnoses(text, file_id))
        
        # LLM fallback: if we found very few events or text is complex, use LLM
        if len(events) < 3 and len(text) > 500:
            llm_events = LLMExtractor.extract_healthcare_events(text)
            # Convert LLM events to our format and merge (avoid duplicates)
            converted_events = self._convert_llm_events(llm_events, file_id, text)
            # Only add events that don't duplicate existing ones
            existing_keys = set()
            for e in events:
                key = f"{e.get('type')}_{e.get('test', e.get('name', e.get('condition', '')))}"
                existing_keys.add(key)
            
            for e in converted_events:
                key = f"{e.get('type')}_{e.get('test', e.get('name', e.get('condition', '')))}"
                if key not in existing_keys:
                    events.append(e)
                    existing_keys.add(key)
        
        return {
            "events": events
        }
    
    def _convert_llm_events(self, llm_events: List[Dict], file_id: str, text: str) -> List[Dict]:
        """Convert LLM-extracted events to our standard format"""
        converted = []
        
        for llm_event in llm_events:
            event_type = llm_event.get("type", "")
            
            if event_type == "lab_result":
                event = {
                    "event_id": self.generate_event_id("lab"),
                    "type": "lab_result",
                    "test": llm_event.get("test", "UNKNOWN").upper(),
                    "value": float(llm_event.get("value", 0)) if llm_event.get("value") else 0,
                    "units": llm_event.get("units", "unknown"),
                    "ref_range": llm_event.get("ref_range", "N/A"),
                    "date": llm_event.get("date"),
                    "confidence": 0.85,  # LLM extraction confidence
                    "provenance": [self.create_provenance(file_id, snippet=text[:200])]
                }
                # Check if abnormal
                ref_range = llm_event.get("ref_range", "")
                if "-" in ref_range:
                    try:
                        parts = ref_range.split("-")
                        min_val = float(parts[0].strip())
                        max_val = float(parts[1].strip())
                        value = event["value"]
                        if value < min_val or value > max_val:
                            event["abnormal"] = True
                    except:
                        pass
                converted.append(event)
            
            elif event_type == "medication":
                event = {
                    "event_id": self.generate_event_id("med"),
                    "type": "medication",
                    "name": llm_event.get("name", "Unknown"),
                    "dose": llm_event.get("dose", "unknown"),
                    "frequency": llm_event.get("frequency", "as prescribed"),
                    "start_date": llm_event.get("date"),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=text[:200])]
                }
                converted.append(event)
            
            elif event_type == "diagnosis":
                event = {
                    "event_id": self.generate_event_id("diag"),
                    "type": "diagnosis",
                    "condition": llm_event.get("condition", "Unknown"),
                    "date": llm_event.get("date"),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=text[:200])]
                }
                converted.append(event)
        
        return converted
    
    def _extract_lab_results(self, text: str, file_id: str) -> List[Dict]:
        """Extract lab test results - works for any lab test"""
        events = []
        text_lower = text.lower()
        
        # First, extract known patterns
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
                    
                    # Determine units based on test
                    units_map = {
                        'hba1c': '%',
                        'bp': 'mmHg',
                        'tsh': 'mIU/L',
                        'alt': 'U/L',
                        'ast': 'U/L',
                        'hemoglobin': 'g/dl',
                        'creatinine': 'mg/dl'
                    }
                    units = units_map.get(test_name, 'mg/dl')
                    
                    event = {
                        "event_id": self.generate_event_id("lab"),
                        "type": "lab_result",
                        "test": test_name.upper(),
                        "value": value,
                        "units": units,
                        "ref_range": f"{ref_range.get('min', 'N/A')}-{ref_range.get('max', 'N/A')}",
                        "date": self._extract_date_near_match(text, match.start()),
                        "confidence": 0.9,
                        "provenance": [self.create_provenance(file_id, snippet=snippet)]
                    }
                    
                    # Check if abnormal (for HDL, higher is better, so reverse logic)
                    if ref_range:
                        if test_name == 'hdl':
                            # HDL: lower than min is abnormal
                            if value < ref_range.get('min', 0):
                                event["abnormal"] = True
                        else:
                            # Other tests: outside range is abnormal
                            if value < ref_range.get('min', 0) or value > ref_range.get('max', 999):
                                event["abnormal"] = True
                    
                    events.append(event)
                except ValueError:
                    continue
        
        # Also try to extract generic lab patterns (test name : value)
        # This catches tests not in our predefined list
        generic_pattern = r'([A-Z]{2,10}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[:\s]+([0-9.]+)\s*(?:mg/dl|g/dl|%|U/L|mIU/L)?'
        matches = re.finditer(generic_pattern, text)
        for match in matches:
            test_name = match.group(1).strip()
            value_str = match.group(2)
            
            # Skip if already extracted or if it's not a lab test
            if any(test_name.upper() in e.get("test", "") for e in events):
                continue
            
            # Skip common false positives
            skip_words = ['DATE', 'TIME', 'AGE', 'PHONE', 'ID', 'NO', 'NUMBER']
            if test_name.upper() in skip_words:
                continue
            
            try:
                value = float(value_str)
                # Only add if it looks like a lab value (reasonable range)
                if 0.1 <= value <= 10000:
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    snippet = text[start:end]
                    
                    events.append({
                        "event_id": self.generate_event_id("lab"),
                        "type": "lab_result",
                        "test": test_name.upper(),
                        "value": value,
                        "units": "unknown",
                        "ref_range": "N/A",
                        "date": self._extract_date_near_match(text, match.start()),
                        "confidence": 0.6,  # Lower confidence for generic extraction
                        "provenance": [self.create_provenance(file_id, snippet=snippet)]
                    })
            except ValueError:
                continue
        
        return events
    
    def _extract_medications(self, text: str, file_id: str) -> List[Dict]:
        """Extract medication information - works for any medication"""
        events = []
        found_meds = set()
        
        # Common medication keywords (extended list)
        med_keywords = [
            'metformin', 'insulin', 'aspirin', 'atorvastatin', 'amlodipine',
            'lisinopril', 'metoprolol', 'losartan', 'omeprazole', 'simvastatin',
            'levothyroxine', 'gabapentin', 'hydrochlorothiazide', 'sertraline',
            'albuterol', 'prednisone', 'warfarin', 'furosemide', 'tramadol'
        ]
        
        # Extract known medications
        for keyword in med_keywords:
            pattern = rf'\b{keyword}\b[:\s]+([0-9.]+)\s*(?:mg|g|ml|mcg)?'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dose = match.group(1) if match.lastindex else "unknown"
                med_name = keyword.capitalize()
                
                if med_name not in found_meds:
                    found_meds.add(med_name)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    snippet = text[start:end]
                    
                    events.append({
                        "event_id": self.generate_event_id("med"),
                        "type": "medication",
                        "name": med_name,
                        "dose": f"{dose} mg",
                        "frequency": self._extract_frequency(text, match.start()),
                        "start_date": self._extract_date_near_match(text, match.start()),
                        "confidence": 0.85,
                        "provenance": [self.create_provenance(file_id, snippet=snippet)]
                    })
        
        # Generic medication patterns (catches medications not in keyword list)
        med_patterns = [
            r'(?:Prescribed|Medication|Drug|Rx)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+)\s*(?:mg|g|ml|mcg)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+)\s*(?:mg|g|ml|mcg)\s*(?:daily|twice|once|BID|TID|QID)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+tablet[s]?\s+(\d+)\s*(?:mg|g)?',
        ]
        
        for pattern in med_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                med_name = match.group(1).strip()
                dose = match.group(2) if match.lastindex >= 2 else "unknown"
                
                # Skip if already found or if it's a common false positive
                if med_name in found_meds or len(med_name) < 3:
                    continue
                
                skip_words = ['Patient', 'Doctor', 'Date', 'Time', 'Name', 'Age']
                if med_name in skip_words:
                    continue
                
                found_meds.add(med_name)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                snippet = text[start:end]
                
                events.append({
                    "event_id": self.generate_event_id("med"),
                    "type": "medication",
                    "name": med_name,
                    "dose": f"{dose} mg",
                    "frequency": self._extract_frequency(text, match.start()),
                    "start_date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.7,  # Lower confidence for generic extraction
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        
        return events
    
    def _extract_diagnoses(self, text: str, file_id: str) -> List[Dict]:
        """Extract diagnoses - works for any health condition"""
        events = []
        text_lower = text.lower()
        
        # Extended list of common conditions (can detect any of these)
        diagnosis_keywords = [
            'diabetes', 'hypertension', 'asthma', 'copd', 'anemia',
            'hypothyroidism', 'hyperthyroidism', 'thyroid',
            'kidney disease', 'renal', 'ckd',
            'liver disease', 'hepatitis', 'cirrhosis',
            'heart disease', 'cardiac', 'arrhythmia', 'chf',
            'arthritis', 'osteoporosis', 'osteopenia',
            'depression', 'anxiety', 'mental health',
            'cancer', 'tumor', 'malignancy',
            'pneumonia', 'bronchitis', 'infection',
            'allergy', 'allergic'
        ]
        
        # Also look for diagnosis patterns
        diagnosis_patterns = [
            r'(?:diagnosis|diagnosed|condition|disease)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:diagnosis|disease|disorder)',
        ]
        
        found_conditions = set()
        
        # Extract from keywords
        for keyword in diagnosis_keywords:
            pattern = rf'\b{keyword}\b'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                condition = keyword.capitalize()
                if condition not in found_conditions:
                    found_conditions.add(condition)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    snippet = text[start:end]
                    
                    events.append({
                        "event_id": self.generate_event_id("diag"),
                        "type": "diagnosis",
                        "condition": condition,
                        "date": self._extract_date_near_match(text, match.start()),
                        "confidence": 0.8,
                        "provenance": [self.create_provenance(file_id, snippet=snippet)]
                    })
        
        # Extract from patterns (more flexible)
        for pattern in diagnosis_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                condition = match.group(1).strip()
                # Filter out common false positives
                if len(condition) > 3 and condition.lower() not in ['the', 'and', 'for', 'with', 'from']:
                    if condition not in found_conditions:
                        found_conditions.add(condition)
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        snippet = text[start:end]
                        
                        events.append({
                            "event_id": self.generate_event_id("diag"),
                            "type": "diagnosis",
                            "condition": condition,
                            "date": self._extract_date_near_match(text, match.start()),
                            "confidence": 0.7,  # Lower confidence for pattern-based
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

