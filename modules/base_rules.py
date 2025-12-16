"""
Base rules class for risk detection
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseRules(ABC):
    """Base class for sector-specific risk rules"""
    
    @abstractmethod
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """
        Detect risks from events and timeline
        
        Returns:
        [
            {
                "risk": "GST mismatch",
                "severity": "high",
                "event_ids": [...],
                "explanation": "..."
            }
        ]
        """
        pass

