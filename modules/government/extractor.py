"""
Government Sector Extractor
Comprehensive extraction: applications, certificates, renewals, 
deadlines, compliance documents, status tracking
"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor
from modules.llm_extractor import LLMExtractor


class GovernmentExtractor(BaseExtractor):
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract government document events - comprehensive"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract applications
        events.extend(self._extract_applications(text, file_id))
        
        # Extract certificates
        events.extend(self._extract_certificates(text, file_id))
        
        # Extract renewals
        events.extend(self._extract_renewals(text, file_id))
        
        # Extract compliance documents
        events.extend(self._extract_compliance(text, file_id))
        
        # Extract deadlines
        events.extend(self._extract_deadlines(text, file_id))
        
        # Extract status updates
        events.extend(self._extract_status_updates(text, file_id))
        
        return {"events": events}
    
    def _extract_applications(self, text: str, file_id: str) -> List[Dict]:
        """Extract application information"""
        events = []
        patterns = [
            r'(?:application|APP|application\s*no)[:\s#]+([A-Z0-9\-]+)',
            r'Application\s*ID[:\s]+([A-Z0-9\-]+)',
            r'Ref[:\s]+([A-Z0-9\-/]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("app"),
                    "type": "application",
                    "app_id": match.group(1),
                    "app_type": self._extract_application_type(text),
                    "status": self._extract_status(text),
                    "submitted_date": self._extract_date_near_match(text, match.start()),
                    "deadline": self._extract_deadline(text),
                    "confidence": 0.9,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_certificates(self, text: str, file_id: str) -> List[Dict]:
        """Extract certificate information"""
        events = []
        certificate_types = [
            'license', 'permit', 'certificate', 'registration', 
            'clearance', 'approval', 'authorization'
        ]
        
        for cert_type in certificate_types:
            pattern = rf'(?:{cert_type}|{cert_type.upper()})[:\s#]+([A-Z0-9\-]+)'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("cert"),
                    "type": "certificate",
                    "cert_id": match.group(1),
                    "cert_type": cert_type,
                    "issue_date": self._extract_date_near_match(text, match.start()),
                    "expiry_date": self._extract_expiry(text),
                    "status": self._extract_status(text),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_renewals(self, text: str, file_id: str) -> List[Dict]:
        """Extract renewal information"""
        events = []
        pattern = r'(?:renewal|renew)[:\s]+([A-Z0-9\-]+)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
            events.append({
                "event_id": self.generate_event_id("ren"),
                "type": "renewal",
                "renewal_id": match.group(1),
                "renewal_date": self._extract_date_near_match(text, match.start()),
                "next_renewal": self._extract_next_renewal(text),
                "status": self._extract_status(text),
                "confidence": 0.85,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        return events
    
    def _extract_compliance(self, text: str, file_id: str) -> List[Dict]:
        """Extract compliance document information"""
        events = []
        compliance_keywords = [
            'audit', 'inspection', 'compliance', 'verification', 
            'assessment', 'review', 'check'
        ]
        
        for keyword in compliance_keywords:
            pattern = rf'\b{keyword}\b[:\s]+([A-Z0-9\-]+)'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("comp"),
                    "type": "compliance",
                    "compliance_id": match.group(1),
                    "compliance_type": keyword,
                    "date": self._extract_date_near_match(text, match.start()),
                    "status": self._extract_status(text),
                    "confidence": 0.8,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_deadlines(self, text: str, file_id: str) -> List[Dict]:
        """Extract deadline information"""
        events = []
        patterns = [
            r'(?:deadline|due\s*date|expires|expiry)[:\s]+(\d{4}-\d{2}-\d{2})',
            r'(?:deadline|due\s*date|expires|expiry)[:\s]+(\d{2}/\d{2}/\d{4})',
            r'(?:deadline|due\s*date|expires|expiry)[:\s]+(\d{2}-\d{2}-\d{4})',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                deadline = match.group(1)
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("dead"),
                    "type": "deadline",
                    "deadline_date": deadline,
                    "related_doc": self._extract_related_document(text, match.start()),
                    "confidence": 0.9,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_status_updates(self, text: str, file_id: str) -> List[Dict]:
        """Extract status update information"""
        events = []
        status_keywords = {
            "approved": r'\bapproved\b',
            "rejected": r'\b(?:rejected|denied|refused)\b',
            "pending": r'\b(?:pending|under\s*review|processing)\b',
            "completed": r'\b(?:completed|done|finished)\b',
            "expired": r'\bexpired\b',
            "revoked": r'\b(?:revoked|cancelled|canceled)\b',
        }
        
        for status, pattern in status_keywords.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("stat"),
                    "type": "status_update",
                    "status": status,
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_application_type(self, text: str) -> str:
        """Extract application type"""
        types = ['license', 'permit', 'certificate', 'registration', 'renewal']
        text_lower = text.lower()
        for app_type in types:
            if app_type in text_lower:
                return app_type
        return "unknown"
    
    def _extract_status(self, text: str) -> str:
        """Extract document status"""
        text_lower = text.lower()
        if "approved" in text_lower:
            return "approved"
        elif "rejected" in text_lower or "denied" in text_lower:
            return "rejected"
        elif "pending" in text_lower or "under review" in text_lower:
            return "pending"
        elif "expired" in text_lower:
            return "expired"
        elif "revoked" in text_lower or "cancelled" in text_lower:
            return "revoked"
        return "submitted"
    
    def _extract_deadline(self, text: str) -> str:
        """Extract deadline"""
        patterns = [
            r'(?:deadline|due|expires)[:\s]+(\d{4}-\d{2}-\d{2})',
            r'(?:deadline|due|expires)[:\s]+(\d{2}/\d{2}/\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_expiry(self, text: str) -> str:
        """Extract expiry date"""
        patterns = [
            r'(?:expires|expiry|valid\s*until)[:\s]+(\d{4}-\d{2}-\d{2})',
            r'(?:expires|expiry|valid\s*until)[:\s]+(\d{2}/\d{2}/\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_next_renewal(self, text: str) -> str:
        """Extract next renewal date"""
        pattern = r'(?:next\s*renewal|renew\s*by)[:\s]+(\d{4}-\d{2}-\d{2})'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _extract_related_document(self, text: str, position: int) -> str:
        """Extract related document ID near deadline"""
        start = max(0, position - 100)
        end = min(len(text), position + 100)
        context = text[start:end]
        
        # Look for document IDs near deadline
        doc_patterns = [
            r'(?:application|APP|certificate|license)[:\s#]+([A-Z0-9\-]+)',
            r'Ref[:\s]+([A-Z0-9\-/]+)',
        ]
        for pattern in doc_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_date_near_match(self, text: str, position: int) -> str:
        """Extract date near match position"""
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

