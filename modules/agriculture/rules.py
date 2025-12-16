"""Agriculture Risk Rules"""
from modules.base_rules import BaseRules
from typing import List, Dict


class AgricultureRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        risks = []
        for event in events:
            if event.get("type") == "soil_moisture" and event.get("value", 100) < 18:
                risks.append({
                    "risk": "Low soil moisture",
                    "severity": "medium",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"Soil moisture {event.get('value')}% is below threshold (18%)"
                })
        return risks

