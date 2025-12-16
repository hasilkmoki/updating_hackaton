"""Kirana Risk Rules"""
from modules.base_rules import BaseRules
from typing import List, Dict


class KiranaRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        risks = []
        for event in events:
            if event.get("type") == "bill" and not event.get("paid"):
                risks.append({
                    "risk": "Unpaid bill",
                    "severity": "medium",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"Bill {event.get('bill_no')} is unpaid"
                })
        return risks

