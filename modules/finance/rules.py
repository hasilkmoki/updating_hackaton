"""
Finance Sector Risk Rules
Comprehensive risk detection: GST validation, duplicates, 
late payments, payment matching, amount discrepancies
"""
from modules.base_rules import BaseRules
from typing import List, Dict
from datetime import datetime, timedelta


class FinanceRules(BaseRules):
    """Finance-specific risk detection"""
    
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect comprehensive finance risks"""
        risks = []
        timeline = timeline or []
        all_events = events + timeline
        
        # Check GST mismatches and validation
        risks.extend(self._check_gst_mismatch(events))
        risks.extend(self._check_gst_validation(events))
        
        # Check for duplicates
        risks.extend(self._check_duplicates(events, timeline))
        
        # Check late payments
        risks.extend(self._check_late_payments(events, timeline))
        
        # Check payment matching
        risks.extend(self._check_payment_matching(all_events))
        
        # Check amount discrepancies
        risks.extend(self._check_amount_discrepancies(events))
        
        # Check GSTIN validation
        risks.extend(self._check_gstin_validation(events))
        
        return risks
    
    def _check_gst_mismatch(self, events: List[Dict]) -> List[Dict]:
        """Check for GST calculation mismatches - comprehensive validation"""
        risks = []
        
        for event in events:
            if event.get("type") == "invoice":
                taxable = event.get("taxable_total", 0)
                gst_percent = event.get("gst_percent", 0)
                gst_amount = event.get("gst_amount", 0)
                cgst = event.get("cgst", 0)
                sgst = event.get("sgst", 0)
                
                # Check CGST + SGST = Total GST
                if cgst > 0 and sgst > 0:
                    expected_total = cgst + sgst
                    if abs(gst_amount - expected_total) > 0.01:
                        risks.append({
                            "risk": "CGST + SGST mismatch",
                            "severity": "high",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"CGST ({cgst}) + SGST ({sgst}) = {expected_total:.2f}, but total GST is {gst_amount:.2f}"
                        })
                
                # Check GST calculation from taxable amount
                if taxable > 0 and gst_percent > 0:
                    expected_gst = taxable * gst_percent / 100
                    tolerance = max(1.0, expected_gst * 0.01)  # 1% tolerance or minimum ₹1
                    
                    if abs(gst_amount - expected_gst) > tolerance:
                        diff = abs(gst_amount - expected_gst)
                        risks.append({
                            "risk": "GST calculation mismatch",
                            "severity": "high",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"GST amount ₹{gst_amount:.2f} does not match computed ₹{expected_gst:.2f} (expected {gst_percent}% of ₹{taxable:.2f}). Difference: ₹{diff:.2f}"
                        })
                
                # Check if total = taxable + GST
                total = event.get("total", 0)
                if total > 0 and taxable > 0 and gst_amount > 0:
                    expected_total = taxable + gst_amount
                    tolerance = max(1.0, expected_total * 0.01)
                    
                    if abs(total - expected_total) > tolerance:
                        risks.append({
                            "risk": "Total amount mismatch",
                            "severity": "high",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"Total ₹{total:.2f} does not equal Taxable (₹{taxable:.2f}) + GST (₹{gst_amount:.2f}) = ₹{expected_total:.2f}"
                        })
        
        return risks
    
    def _check_gst_validation(self, events: List[Dict]) -> List[Dict]:
        """Validate GST percentage and structure"""
        risks = []
        
        valid_gst_percents = [0, 5, 12, 18, 28]  # Standard GST rates in India
        
        for event in events:
            if event.get("type") == "invoice":
                gst_percent = event.get("gst_percent", 0)
                
                # Check if GST percent is valid
                if gst_percent > 0 and gst_percent not in valid_gst_percents:
                    risks.append({
                        "risk": "Invalid GST percentage",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"GST percentage {gst_percent}% is not a standard rate. Valid rates: 0%, 5%, 12%, 18%, 28%"
                    })
                
                # Check if GST is applied but taxable is 0
                if gst_percent > 0 and event.get("taxable_total", 0) == 0:
                    risks.append({
                        "risk": "GST applied to zero taxable amount",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"GST {gst_percent}% is applied but taxable amount is ₹0"
                    })
        
        return risks
    
    def _check_gstin_validation(self, events: List[Dict]) -> List[Dict]:
        """Validate GSTIN format"""
        risks = []
        
        for event in events:
            if event.get("type") == "invoice":
                gstin = event.get("gstin")
                
                if gstin:
                    # GSTIN format: 15 characters, 2 digits + 10 alphanumeric + 1 Z + 1 alphanumeric
                    gstin_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
                    import re
                    if not re.match(gstin_pattern, gstin.upper()):
                        risks.append({
                            "risk": "Invalid GSTIN format",
                            "severity": "medium",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"GSTIN {gstin} does not match standard format (15 characters: 2 digits + 10 alphanumeric + Z + 1 alphanumeric)"
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
        """Check for late payments - comprehensive tracking"""
        risks = []
        
        all_invoices = [e for e in events + timeline if e.get("type") == "invoice"]
        all_payments = [e for e in events + timeline if e.get("type") == "payment"]
        
        for invoice in all_invoices:
            invoice_no = invoice.get("invoice_no")
            invoice_date_str = invoice.get("date")
            invoice_amount = invoice.get("total", 0)
            
            if not invoice_date_str:
                continue
            
            try:
                # Parse date (handle multiple formats)
                invoice_date = self._parse_date(invoice_date_str)
                if not invoice_date:
                    continue
                
                days_old = (datetime.now() - invoice_date).days
                
                # Check if payment exists for this invoice
                payment_found = False
                total_paid = 0
                
                for payment in all_payments:
                    payment_amount = payment.get("amount", 0)
                    # Simple matching: if payment amount matches invoice amount (within 1%)
                    if abs(payment_amount - invoice_amount) < max(1.0, invoice_amount * 0.01):
                        payment_found = True
                        total_paid += payment_amount
                
                # Determine severity based on days overdue
                if not payment_found:
                    if days_old > 60:
                        severity = "high"
                    elif days_old > 30:
                        severity = "medium"
                    else:
                        continue  # Not overdue yet
                    
                    risks.append({
                        "risk": "Overdue invoice - payment pending",
                        "severity": severity,
                        "event_ids": [invoice.get("event_id")],
                        "explanation": f"Invoice {invoice_no} (₹{invoice_amount:.2f}) is {days_old} days old. Payment not found."
                    })
                elif total_paid < invoice_amount * 0.99:  # Partial payment
                    remaining = invoice_amount - total_paid
                    risks.append({
                        "risk": "Partial payment detected",
                        "severity": "medium",
                        "event_ids": [invoice.get("event_id")],
                        "explanation": f"Invoice {invoice_no} total: ₹{invoice_amount:.2f}, Paid: ₹{total_paid:.2f}, Remaining: ₹{remaining:.2f}"
                    })
            except Exception as e:
                pass
        
        return risks
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats"""
        if not date_str:
            return None
        
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d/%m/%y",
            "%d-%m-%y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        return None
    
    def _check_payment_matching(self, events: List[Dict]) -> List[Dict]:
        """Check if payments match invoices"""
        risks = []
        
        invoices = [e for e in events if e.get("type") == "invoice"]
        payments = [e for e in events if e.get("type") == "payment"]
        
        # Check for orphaned payments (no matching invoice)
        for payment in payments:
            payment_amount = payment.get("amount", 0)
            payment_date = payment.get("date")
            
            # Try to find matching invoice
            matched = False
            for invoice in invoices:
                invoice_amount = invoice.get("total", 0)
                invoice_date = invoice.get("date")
                
                # Match by amount (within 1%) and date proximity
                if abs(payment_amount - invoice_amount) < max(1.0, invoice_amount * 0.01):
                    matched = True
                    break
            
            if not matched and payment_amount > 0:
                risks.append({
                    "risk": "Unmatched payment",
                    "severity": "low",
                    "event_ids": [payment.get("event_id")],
                    "explanation": f"Payment of ₹{payment_amount:.2f} on {payment_date} does not match any invoice"
                })
        
        return risks
    
    def _check_amount_discrepancies(self, events: List[Dict]) -> List[Dict]:
        """Check for amount calculation discrepancies"""
        risks = []
        
        for event in events:
            if event.get("type") == "invoice":
                line_items = event.get("line_items", [])
                taxable = event.get("taxable_total", 0)
                
                if line_items:
                    # Calculate total from line items
                    calculated_total = 0
                    for item in line_items:
                        qty = item.get("qty", 0)
                        unit_price = item.get("unit_price", 0)
                        item_total = item.get("total", qty * unit_price)
                        calculated_total += item_total
                    
                    # Compare with taxable total
                    if taxable > 0 and abs(calculated_total - taxable) > max(1.0, taxable * 0.01):
                        risks.append({
                            "risk": "Line items total mismatch",
                            "severity": "medium",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"Sum of line items (₹{calculated_total:.2f}) does not match taxable total (₹{taxable:.2f})"
                        })
        
        return risks

