"""Government Risk Rules"""
from modules.base_rules import BaseRules
from typing import List, Dict
from datetime import datetime


class GovernmentRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        risks = []
        for event in events:
            if event.get("type") == "application" and event.get("deadline"):
                try:
                    deadline = datetime.strptime(event["deadline"], "%Y-%m-%d")
                    days_left = (deadline - datetime.now()).days
                    if 0 < days_left <= 30:
                        risks.append({
                            "risk": "Upcoming deadline",
                            "severity": "medium",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"Application {event.get('app_id')} deadline in {days_left} days"
                        })
                except:
                    pass
        return risks

