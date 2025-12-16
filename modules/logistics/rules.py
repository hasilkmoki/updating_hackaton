"""Logistics Risk Rules"""
from modules.base_rules import BaseRules
from typing import List, Dict


class LogisticsRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        risks = []
        for event in events:
            if event.get("type") == "temperature" and event.get("value", 0) > 8:
                risks.append({
                    "risk": "Temperature breach",
                    "severity": "high",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"Temperature {event.get('value')}°C exceeds allowed 8°C"
                })
        return risks

