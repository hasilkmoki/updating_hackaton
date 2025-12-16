"""
Finance Sector Risk Rules
Detects GST mismatches, duplicates, late payments
"""
from modules.base_rules import BaseRules
from typing import List, Dict


class FinanceRules(BaseRules):
    """Finance-specific risk detection"""
    
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect finance risks"""
        risks = []
        timeline = timeline or []
        
        # Check GST mismatches
        risks.extend(self._check_gst_mismatch(events))
        
        # Check for duplicates
        risks.extend(self._check_duplicates(events, timeline))
        
        # Check late payments
        risks.extend(self._check_late_payments(events, timeline))
        
        return risks
    
    def _check_gst_mismatch(self, events: List[Dict]) -> List[Dict]:
        """Check for GST calculation mismatches"""
        risks = []
        
        for event in events:
            if event.get("type") == "invoice":
                taxable = event.get("taxable_total", 0)
                gst_percent = event.get("gst_percent", 0)
                gst_amount = event.get("gst_amount", 0)
                
                if taxable > 0 and gst_percent > 0:
                    expected_gst = taxable * gst_percent / 100
                    tolerance = 0.5  # Allow 0.5% rounding error
                    
                    if abs(gst_amount - expected_gst) > tolerance:
                        risks.append({
                            "risk": "GST mismatch",
                            "severity": "high",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"GST amount {gst_amount} does not match computed {expected_gst:.2f} (expected {gst_percent}% of {taxable})"
                        })
        
        return risks
    
    def _check_duplicates(self, events: List[Dict], timeline: List[Dict]) -> List[Dict]:
        """Check for duplicate invoices"""
        risks = []
        
        all_invoices = [e for e in events + timeline if e.get("type") == "invoice"]
        invoice_map = {}
        
        for inv in all_invoices:
            inv_no = inv.get("invoice_no")
            vendor = inv.get("vendor", "")
            amount = inv.get("total", 0)
            
            if inv_no:
                key = f"{inv_no}_{vendor}"
                if key in invoice_map:
                    risks.append({
                        "risk": "Duplicate invoice detected",
                        "severity": "medium",
                        "event_ids": [inv.get("event_id"), invoice_map[key].get("event_id")],
                        "explanation": f"Invoice {inv_no} from {vendor} appears multiple times"
                    })
                else:
                    invoice_map[key] = inv
        
        return risks
    
    def _check_late_payments(self, events: List[Dict], timeline: List[Dict]) -> List[Dict]:
        """Check for late payments (simplified)"""
        risks = []
        
        from datetime import datetime, timedelta
        
        for event in events + timeline:
            if event.get("type") == "invoice":
                date_str = event.get("date")
                if date_str:
                    try:
                        # Parse date (simplified)
                        if "/" in date_str:
                            parts = date_str.split("/")
                            if len(parts) == 3:
                                invoice_date = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                                days_old = (datetime.now() - invoice_date).days
                                
                                # Check if unpaid and > 30 days old
                                if days_old > 30:  # Assuming unpaid if no payment event
                                    risks.append({
                                        "risk": "Late payment",
                                        "severity": "medium",
                                        "event_ids": [event.get("event_id")],
                                        "explanation": f"Invoice {event.get('invoice_no')} is {days_old} days old and may be overdue"
                                    })
                    except:
                        pass
        
        return risks

