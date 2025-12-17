"""
Government Risk Rules
Comprehensive risk detection: deadline tracking, expiry alerts,
compliance issues, missing documents, status monitoring
"""
from modules.base_rules import BaseRules
from typing import List, Dict
from datetime import datetime, timedelta


class GovernmentRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect comprehensive government document risks"""
        risks = []
        timeline = timeline or []
        all_events = events + timeline
        
        # Deadline tracking
        risks.extend(self._check_upcoming_deadlines(all_events))
        risks.extend(self._check_overdue_deadlines(all_events))
        
        # Expiry monitoring
        risks.extend(self._check_expiring_certificates(all_events))
        risks.extend(self._check_expired_documents(all_events))
        
        # Compliance issues
        risks.extend(self._check_compliance_status(all_events))
        risks.extend(self._check_missing_documents(all_events))
        
        # Status monitoring
        risks.extend(self._check_rejected_applications(events))
        risks.extend(self._check_pending_delays(all_events))
        
        # Renewal tracking
        risks.extend(self._check_renewal_reminders(all_events))
        
        return risks
    
    def _check_upcoming_deadlines(self, events: List[Dict]) -> List[Dict]:
        """Check for upcoming deadlines"""
        risks = []
        for event in events:
            deadline = event.get("deadline") or event.get("deadline_date")
            if not deadline:
                continue
            
            try:
                deadline_date = self._parse_date(deadline)
                if not deadline_date:
                    continue
                
                days_left = (deadline_date - datetime.now()).days
                
                if days_left < 0:
                    continue  # Handled by overdue check
                elif days_left <= 7:
                    severity = "high"
                elif days_left <= 30:
                    severity = "medium"
                else:
                    continue
                
                event_type = event.get("type", "document")
                doc_id = event.get("app_id") or event.get("cert_id") or event.get("compliance_id") or "N/A"
                
                risks.append({
                    "risk": f"Upcoming deadline - {days_left} days remaining",
                    "severity": severity,
                    "event_ids": [event.get("event_id")],
                    "explanation": f"{event_type.capitalize()} {doc_id} deadline is in {days_left} days ({deadline}). Take action immediately."
                })
            except:
                pass
        
        return risks
    
    def _check_overdue_deadlines(self, events: List[Dict]) -> List[Dict]:
        """Check for overdue deadlines"""
        risks = []
        for event in events:
            deadline = event.get("deadline") or event.get("deadline_date")
            if not deadline:
                continue
            
            try:
                deadline_date = self._parse_date(deadline)
                if not deadline_date:
                    continue
                
                days_overdue = (datetime.now() - deadline_date).days
                
                if days_overdue > 0:
                    event_type = event.get("type", "document")
                    doc_id = event.get("app_id") or event.get("cert_id") or event.get("compliance_id") or "N/A"
                    
                    risks.append({
                        "risk": f"OVERDUE: Deadline passed {days_overdue} days ago",
                        "severity": "critical" if days_overdue > 30 else "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"{event_type.capitalize()} {doc_id} deadline was {days_overdue} days ago ({deadline}). Immediate action required."
                    })
            except:
                pass
        
        return risks
    
    def _check_expiring_certificates(self, events: List[Dict]) -> List[Dict]:
        """Check for expiring certificates"""
        risks = []
        for event in events:
            if event.get("type") == "certificate":
                expiry = event.get("expiry_date")
                if not expiry:
                    continue
                
                try:
                    expiry_date = self._parse_date(expiry)
                    if not expiry_date:
                        continue
                    
                    days_until_expiry = (expiry_date - datetime.now()).days
                    
                    if days_until_expiry < 0:
                        continue  # Handled by expired check
                    elif days_until_expiry <= 30:
                        cert_id = event.get("cert_id", "N/A")
                        cert_type = event.get("cert_type", "certificate")
                        
                        risks.append({
                            "risk": f"Certificate expiring soon - {days_until_expiry} days",
                            "severity": "high" if days_until_expiry <= 7 else "medium",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"{cert_type.capitalize()} {cert_id} expires in {days_until_expiry} days ({expiry}). Renew immediately."
                        })
                except:
                    pass
        
        return risks
    
    def _check_expired_documents(self, events: List[Dict]) -> List[Dict]:
        """Check for expired documents"""
        risks = []
        for event in events:
            expiry = event.get("expiry_date")
            if not expiry:
                continue
            
            try:
                expiry_date = self._parse_date(expiry)
                if not expiry_date:
                    continue
                
                days_expired = (datetime.now() - expiry_date).days
                
                if days_expired > 0:
                    event_type = event.get("type", "document")
                    doc_id = event.get("cert_id") or event.get("app_id") or "N/A"
                    
                    risks.append({
                        "risk": f"EXPIRED: Document expired {days_expired} days ago",
                        "severity": "critical",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"{event_type.capitalize()} {doc_id} expired {days_expired} days ago ({expiry}). Renewal required immediately."
                    })
            except:
                pass
        
        return risks
    
    def _check_compliance_status(self, events: List[Dict]) -> List[Dict]:
        """Check compliance document status"""
        risks = []
        for event in events:
            if event.get("type") == "compliance":
                status = event.get("status", "").lower()
                compliance_type = event.get("compliance_type", "")
                compliance_id = event.get("compliance_id", "N/A")
                
                if status in ["rejected", "failed", "non-compliant"]:
                    risks.append({
                        "risk": f"Compliance issue: {compliance_type}",
                        "severity": "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"{compliance_type.capitalize()} compliance {compliance_id} has status: {status}. Review and address issues."
                    })
                elif status == "pending" and event.get("date"):
                    # Check if pending too long
                    try:
                        pending_date = self._parse_date(event.get("date"))
                        if pending_date:
                            days_pending = (datetime.now() - pending_date).days
                            if days_pending > 60:
                                risks.append({
                                    "risk": f"Compliance review delayed - {days_pending} days pending",
                                    "severity": "medium",
                                    "event_ids": [event.get("event_id")],
                                    "explanation": f"{compliance_type.capitalize()} compliance has been pending for {days_pending} days. Follow up required."
                                })
                    except:
                        pass
        
        return risks
    
    def _check_missing_documents(self, events: List[Dict]) -> List[Dict]:
        """Check for missing required documents"""
        risks = []
        # Check if application exists but no supporting documents
        applications = [e for e in events if e.get("type") == "application"]
        
        for app in applications:
            app_id = app.get("app_id", "N/A")
            status = app.get("status", "").lower()
            
            # Check if status indicates missing documents
            if "missing" in status or "incomplete" in status or "required" in status:
                risks.append({
                    "risk": "Missing required documents",
                    "severity": "high",
                    "event_ids": [app.get("event_id")],
                    "explanation": f"Application {app_id} indicates missing or incomplete documents. Submit required documents immediately."
                })
        
        return risks
    
    def _check_rejected_applications(self, events: List[Dict]) -> List[Dict]:
        """Check for rejected applications"""
        risks = []
        for event in events:
            if event.get("type") == "application" and event.get("status", "").lower() == "rejected":
                app_id = event.get("app_id", "N/A")
                risks.append({
                    "risk": "Application rejected",
                    "severity": "high",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"Application {app_id} has been rejected. Review rejection reason and resubmit if applicable."
                })
        return risks
    
    def _check_pending_delays(self, events: List[Dict]) -> List[Dict]:
        """Check for applications pending too long"""
        risks = []
        for event in events:
            if event.get("type") == "application" and event.get("status", "").lower() == "pending":
                submitted_date = event.get("submitted_date")
                if submitted_date:
                    try:
                        sub_date = self._parse_date(submitted_date)
                        if sub_date:
                            days_pending = (datetime.now() - sub_date).days
                            if days_pending > 90:
                                app_id = event.get("app_id", "N/A")
                                risks.append({
                                    "risk": f"Application pending too long - {days_pending} days",
                                    "severity": "medium",
                                    "event_ids": [event.get("event_id")],
                                    "explanation": f"Application {app_id} has been pending for {days_pending} days. Follow up with authorities."
                                })
                    except:
                        pass
        return risks
    
    def _check_renewal_reminders(self, events: List[Dict]) -> List[Dict]:
        """Check for renewal reminders"""
        risks = []
        for event in events:
            if event.get("type") == "renewal":
                next_renewal = event.get("next_renewal")
                if next_renewal:
                    try:
                        renewal_date = self._parse_date(next_renewal)
                        if renewal_date:
                            days_until = (renewal_date - datetime.now()).days
                            if 0 < days_until <= 60:
                                renewal_id = event.get("renewal_id", "N/A")
                                risks.append({
                                    "risk": f"Renewal due in {days_until} days",
                                    "severity": "medium" if days_until > 30 else "high",
                                    "event_ids": [event.get("event_id")],
                                    "explanation": f"Renewal {renewal_id} is due in {days_until} days ({next_renewal}). Process renewal."
                                })
                    except:
                        pass
        return risks
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats"""
        if not date_str:
            return None
        
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        return None

