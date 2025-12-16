"""
STEP 6 — ALERTS ENGINE (Sector-Specific Decisions)
Converts risks into actionable alerts
"""
from typing import List, Dict
from datetime import datetime
import uuid

# Import sector rules
from modules.healthcare.rules import HealthcareRules
from modules.finance.rules import FinanceRules
from modules.agriculture.rules import AgricultureRules
from modules.logistics.rules import LogisticsRules
from modules.government.rules import GovernmentRules
from modules.kirana.rules import KiranaRules


class AlertsEngine:
    """Generate alerts from risks"""
    
    def __init__(self):
        self.rules_map = {
            "healthcare": HealthcareRules(),
            "finance": FinanceRules(),
            "agriculture": AgricultureRules(),
            "logistics": LogisticsRules(),
            "government": GovernmentRules(),
            "kirana": KiranaRules()
        }
    
    def generate_alerts(self, risks: List[Dict], events: List[Dict], 
                       timeline: List[Dict], sector: str, file_id: str) -> List[Dict]:
        """
        Generate alerts from risks
        
        Returns:
        [
            {
                "alert_id": "a1",
                "title": "GST mismatch detected",
                "severity": "high",
                "reason": "...",
                "source_file": "file_123",
                "evidence": [...],
                "recommended_actions": [...]
            }
        ]
        """
        alerts = []
        
        for risk in risks:
            alert = {
                "alert_id": f"alert_{uuid.uuid4().hex[:8]}",
                "title": risk.get("risk", "Risk detected"),
                "severity": risk.get("severity", "medium"),
                "reason": risk.get("explanation", ""),
                "source_file": file_id,
                "evidence": self._get_evidence(risk, events),
                "recommended_actions": self._get_actions(risk, sector),
                "created_at": datetime.utcnow().isoformat()
            }
            alerts.append(alert)
        
        return alerts
    
    def _get_evidence(self, risk: Dict, events: List[Dict]) -> List[Dict]:
        """Get evidence snippets for risk"""
        evidence = []
        event_ids = risk.get("event_ids", [])
        
        for event in events:
            if event.get("event_id") in event_ids:
                provenance = event.get("provenance", [])
                for prov in provenance:
                    evidence.append({
                        "file_id": prov.get("file_id"),
                        "snippet": prov.get("snippet", ""),
                        "page": prov.get("page")
                    })
        
        return evidence
    
    def _get_actions(self, risk: Dict, sector: str) -> List[str]:
        """Get recommended actions based on risk and sector"""
        actions_map = {
            "healthcare": {
                "Abnormal": ["Schedule follow-up test", "Consult specialist"],
                "drug interaction": ["Review medication list", "Consult pharmacist"],
                "missing follow-up": ["Schedule appointment", "Contact clinic"]
            },
            "finance": {
                "GST mismatch": ["Review invoice", "Contact vendor"],
                "duplicate": ["Verify invoice", "Check payment status"],
                "late payment": ["Contact vendor", "Process payment"]
            },
            "agriculture": {
                "moisture": ["Irrigate field", "Check irrigation system"],
                "stress": ["Inspect crop", "Contact agronomist"]
            },
            "logistics": {
                "temperature": ["Contact driver", "Divert to cold storage"],
                "delay": ["Update customer", "Check route"]
            },
            "government": {
                "deadline": ["Collect documents", "Submit application"],
                "missing": ["Upload missing document", "Check requirements"]
            },
            "kirana": {
                "unpaid": ["Contact buyer", "Send reminder"],
                "GST filing": ["Reconcile invoices", "Prepare filing"]
            }
        }
        
        sector_actions = actions_map.get(sector, {})
        risk_type = risk.get("risk", "").lower()
        
        for key, actions in sector_actions.items():
            if key in risk_type:
                return actions
        
        return ["Review document", "Take appropriate action"]

