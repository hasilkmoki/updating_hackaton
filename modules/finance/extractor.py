"""
Finance Sector Extractor
Extracts invoice fields, GST, amounts, payments from financial documents
Uses regex patterns + LLM fallback for comprehensive extraction
"""
import re
from typing import Dict, List, Any
from modules.base_extractor import BaseExtractor
from modules.llm_extractor import LLMExtractor


class FinanceExtractor(BaseExtractor):
    """Extract finance events from text"""
    
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract finance events - regex first, LLM fallback for complex cases"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Primary extraction using regex patterns
        invoice_event = self._extract_invoice(text, file_id)
        if invoice_event:
            events.append(invoice_event)
        
        # Extract payment information
        payment_events = self._extract_payments(text, file_id)
        events.extend(payment_events)
        
        # LLM fallback: if invoice extraction failed or incomplete, use LLM
        if not invoice_event or (invoice_event.get("total", 0) == 0 and len(text) > 500):
            llm_data = LLMExtractor.extract_finance_events(text)
            if llm_data and llm_data.get("invoice_no"):
                # Convert LLM data to invoice event format
                llm_invoice = self._convert_llm_invoice(llm_data, file_id, text)
                # Only add if we don't already have a better invoice
                if not invoice_event or invoice_event.get("total", 0) == 0:
                    if invoice_event:
                        events.remove(invoice_event)
                    events.append(llm_invoice)
        
        return {
            "events": events
        }
    
    def _convert_llm_invoice(self, llm_data: Dict, file_id: str, text: str) -> Dict:
        """Convert LLM-extracted data to invoice event format"""
        snippet = text[:500] if len(text) > 500 else text
        
        return {
            "event_id": self.generate_event_id("inv"),
            "type": "invoice",
            "invoice_no": llm_data.get("invoice_no", "UNKNOWN"),
            "date": llm_data.get("date"),
            "vendor": llm_data.get("vendor", "Unknown"),
            "buyer": llm_data.get("buyer"),
            "gstin": llm_data.get("gstin"),
            "line_items": llm_data.get("line_items", []),
            "taxable_total": llm_data.get("taxable_total", 0) or 0,
            "gst_percent": llm_data.get("gst_percent", 0) or 0,
            "gst_amount": llm_data.get("gst_amount", 0) or 0,
            "total": llm_data.get("total", 0) or 0,
            "confidence": 0.85,  # LLM extraction confidence
            "provenance": [self.create_provenance(file_id, snippet=snippet)]
        }
    
    def _extract_payments(self, text: str, file_id: str) -> List[Dict]:
        """Extract payment information"""
        events = []
        
        # Payment patterns
        payment_patterns = [
            r'(?:PAID|PAYMENT|AMOUNT\s*PAID)[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
            r'PAYMENT\s*DATE[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
        ]
        
        amounts = []
        dates = []
        
        for pattern in payment_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.group(1).replace(",", "").replace(".", "").isdigit():
                    try:
                        amounts.append(float(match.group(1).replace(",", "")))
                    except:
                        pass
                else:
                    dates.append(match.group(1))
        
        if amounts:
            snippet = text[:300] if len(text) > 300 else text
            events.append({
                "event_id": self.generate_event_id("pay"),
                "type": "payment",
                "amount": max(amounts),  # Take largest amount
                "date": dates[0] if dates else None,
                "confidence": 0.8,
                "provenance": [self.create_provenance(file_id, snippet=snippet)]
            })
        
        return events
    
    def _extract_invoice(self, text: str, file_id: str) -> Dict:
        """Extract invoice information"""
        text_upper = text.upper()
        
        # Extract invoice number
        invoice_no = None
        invoice_patterns = [
            r'(?:INVOICE|INV|BILL)[\s#:]*([A-Z0-9\-]+)',
            r'INVOICE\s*NO[:\s]+([A-Z0-9\-]+)',
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text_upper)
            if match:
                invoice_no = match.group(1)
                break
        
        # Extract date
        date = self._extract_date(text)
        
        # Extract vendor/buyer
        vendor = self._extract_vendor(text)
        
        # Extract amounts
        amounts = self._extract_amounts(text)
        
        # Extract GST
        gst_info = self._extract_gst(text)
        
        # Extract line items (simplified)
        line_items = self._extract_line_items(text)
        
        # Extract GSTIN
        gstin = self._extract_gstin(text)
        
        if not invoice_no and not amounts:
            return None
        
        snippet = text[:500] if len(text) > 500 else text
        
        return {
            "event_id": self.generate_event_id("inv"),
            "type": "invoice",
            "invoice_no": invoice_no or "UNKNOWN",
            "date": date,
            "vendor": vendor,
            "gstin": gstin,
            "line_items": line_items,
            "taxable_total": amounts.get("taxable", 0),
            "gst_percent": gst_info.get("percent", 0),
            "gst_amount": gst_info.get("amount", 0),
            "total": amounts.get("total", 0),
            "confidence": 0.9 if invoice_no else 0.7,
            "provenance": [self.create_provenance(file_id, snippet=snippet)]
        }
    
    def _extract_date(self, text: str) -> str:
        """Extract invoice date"""
        date_patterns = [
            r'(?:DATE|DATED)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_vendor(self, text: str) -> str:
        """Extract vendor name"""
        patterns = [
            r'(?:FROM|VENDOR|SUPPLIER)[:\s]+([A-Z][A-Za-z\s&]+)',
            r'^([A-Z][A-Za-z\s&]{3,30})\s*(?:PVT|LTD|INC)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return "Unknown"
    
    def _extract_amounts(self, text: str) -> Dict:
        """Extract amounts"""
        amounts = {}
        
        # Extract total
        total_patterns = [
            r'(?:TOTAL|AMOUNT|GRAND\s*TOTAL)[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
            r'[₹Rs]\s*([\d,]+\.?\d*)\s*(?:TOTAL|FINAL)',
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amounts["total"] = float(match.group(1).replace(",", ""))
                break
        
        # Extract taxable value
        taxable_patterns = [
            r'(?:TAXABLE|SUB\s*TOTAL)[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
        ]
        for pattern in taxable_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amounts["taxable"] = float(match.group(1).replace(",", ""))
                break
        
        return amounts
    
    def _extract_gst(self, text: str) -> Dict:
        """Extract GST information - comprehensive"""
        gst_info = {}
        
        # Extract GST percent (5%, 12%, 18%, 28% are common)
        gst_percent_patterns = [
            r'GST[:\s]+(\d+)%',
            r'(\d+)%\s*GST',
            r'GST\s*@\s*(\d+)%',
            r'(\d+)%\s*CGST',
            r'(\d+)%\s*SGST',
        ]
        for pattern in gst_percent_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                percent = int(match.group(1))
                # Validate GST percent (should be 0, 5, 12, 18, or 28)
                if percent in [0, 5, 12, 18, 28]:
                    gst_info["percent"] = percent
                    break
        
        # Extract CGST and SGST separately
        cgst_match = re.search(r'CGST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        sgst_match = re.search(r'SGST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        
        if cgst_match and sgst_match:
            cgst = float(cgst_match.group(1).replace(",", ""))
            sgst = float(sgst_match.group(1).replace(",", ""))
            gst_info["amount"] = cgst + sgst
            gst_info["cgst"] = cgst
            gst_info["sgst"] = sgst
        else:
            # Extract total GST amount
            gst_amount_patterns = [
                r'GST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
                r'TOTAL\s*GST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
            ]
            for pattern in gst_amount_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    gst_info["amount"] = float(match.group(1).replace(",", ""))
                    break
        
        return gst_info
    
    def _extract_gstin(self, text: str) -> str:
        """Extract GSTIN"""
        gstin_pattern = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}'
        match = re.search(gstin_pattern, text)
        if match:
            return match.group(0)
        return None
    
    def _extract_line_items(self, text: str) -> List[Dict]:
        """Extract line items - comprehensive patterns"""
        items = []
        
        # Multiple patterns for line items
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Pattern 1: Description Qty Price Amount
            pattern1 = r'([A-Za-z0-9\s\-&]+)\s+(\d+)\s+[₹Rs]?\s*([\d,]+\.?\d*)\s+[₹Rs]?\s*([\d,]+\.?\d*)'
            match = re.search(pattern1, line, re.IGNORECASE)
            if match:
                items.append({
                    "desc": match.group(1).strip(),
                    "qty": int(match.group(2)),
                    "unit_price": float(match.group(3).replace(",", "")),
                    "total": float(match.group(4).replace(",", ""))
                })
                continue
            
            # Pattern 2: Description Qty Price
            pattern2 = r'([A-Za-z0-9\s\-&]+)\s+(\d+)\s+[₹Rs]?\s*([\d,]+\.?\d*)'
            match = re.search(pattern2, line, re.IGNORECASE)
            if match:
                items.append({
                    "desc": match.group(1).strip(),
                    "qty": int(match.group(2)),
                    "unit_price": float(match.group(3).replace(",", ""))
                })
                continue
            
            # Pattern 3: Description - Amount (single item)
            pattern3 = r'([A-Za-z0-9\s\-&]+)\s+[₹Rs]?\s*([\d,]+\.?\d*)'
            match = re.search(pattern3, line, re.IGNORECASE)
            if match and len(items) < 5:  # Only for first few items to avoid false positives
                # Check if it looks like a line item (not a total/subtotal)
                desc = match.group(1).strip().upper()
                if desc not in ["TOTAL", "SUBTOTAL", "TAXABLE", "GST", "GRAND TOTAL", "AMOUNT"]:
                    items.append({
                        "desc": match.group(1).strip(),
                        "qty": 1,
                        "unit_price": float(match.group(2).replace(",", ""))
                    })
        
        return items[:20]  # Limit to 20 items

