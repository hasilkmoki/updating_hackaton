"""
Healthcare Sector Risk Rules
Detects abnormal values, drug interactions, missing follow-ups
"""
from modules.base_rules import BaseRules
from typing import List, Dict


class HealthcareRules(BaseRules):
    """Healthcare-specific risk detection"""
    
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect healthcare risks"""
        risks = []
        timeline = timeline or []
        
        # Check for abnormal lab values
        risks.extend(self._check_abnormal_labs(events))
        
        # Check for drug interactions (simplified)
        risks.extend(self._check_drug_interactions(events))
        
        # Check for missing follow-ups
        risks.extend(self._check_missing_followups(events, timeline))
        
        return risks
    
    def _check_abnormal_labs(self, events: List[Dict]) -> List[Dict]:
        """Check for abnormal lab values"""
        risks = []
        
        for event in events:
            if event.get("type") == "lab_result" and event.get("abnormal"):
                test = event.get("test", "")
                value = event.get("value", 0)
                ref_range = event.get("ref_range", "")
                
                # Determine severity
                severity = "medium"
                if "hba1c" in test.lower() and value > 8.0:
                    severity = "high"
                elif value > 1.5 * float(ref_range.split("-")[1]) if "-" in ref_range else 0:
                    severity = "high"
                
                risks.append({
                    "risk": f"Abnormal {test} value",
                    "severity": severity,
                    "event_ids": [event.get("event_id")],
                    "explanation": f"{test} = {value} is outside normal range ({ref_range})"
                })
        
        return risks
    
    def _check_drug_interactions(self, events: List[Dict]) -> List[Dict]:
        """Check for potential drug interactions (simplified)"""
        risks = []
        
        # Simple interaction pairs (in real system, use drug interaction database)
        interaction_pairs = [
            ("metformin", "insulin"),
            ("aspirin", "warfarin"),
        ]
        
        meds = [e for e in events if e.get("type") == "medication"]
        med_names = [m.get("name", "").lower() for m in meds]
        
        for med1, med2 in interaction_pairs:
            if med1 in med_names and med2 in med_names:
                risks.append({
                    "risk": f"Potential drug interaction: {med1} + {med2}",
                    "severity": "high",
                    "event_ids": [m.get("event_id") for m in meds if med1 in m.get("name", "").lower() or med2 in m.get("name", "").lower()],
                    "explanation": f"Concurrent use of {med1} and {med2} may cause interactions"
                })
        
        return risks
    
    def _check_missing_followups(self, events: List[Dict], timeline: List[Dict]) -> List[Dict]:
        """Check for missing follow-up tests"""
        risks = []
        
        # Check if diabetes diagnosis exists but no recent HbA1c
        has_diabetes = any(e.get("type") == "diagnosis" and "diabetes" in e.get("condition", "").lower() for e in events + timeline)
        
        if has_diabetes:
            recent_hba1c = any(
                e.get("type") == "lab_result" and "hba1c" in e.get("test", "").lower()
                for e in timeline[-10:]  # Check last 10 events
            )
            
            if not recent_hba1c:
                risks.append({
                    "risk": "Missing HbA1c follow-up for diabetes",
                    "severity": "medium",
                    "event_ids": [],
                    "explanation": "Diabetes diagnosis found but no recent HbA1c test in last 3-6 months"
                })
        
        return risks

