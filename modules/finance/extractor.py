"""
Finance Sector Extractor
Extracts invoice fields, GST, amounts from financial documents
"""
import re
from typing import Dict, List, Any
from modules.base_extractor import BaseExtractor


class FinanceExtractor(BaseExtractor):
    """Extract finance events from text"""
    
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract finance events"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract invoice
        invoice_event = self._extract_invoice(text, file_id)
        if invoice_event:
            events.append(invoice_event)
        
        return {
            "events": events
        }
    
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
        """Extract GST information"""
        gst_info = {}
        
        # Extract GST percent
        gst_percent_patterns = [
            r'GST[:\s]+(\d+)%',
            r'(\d+)%\s*GST',
        ]
        for pattern in gst_percent_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                gst_info["percent"] = int(match.group(1))
                break
        
        # Extract GST amount
        gst_amount_patterns = [
            r'GST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
            r'CGST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
            r'SGST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
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
        """Extract line items (simplified)"""
        items = []
        
        # Simple pattern for line items
        lines = text.split('\n')
        for line in lines:
            # Look for lines with qty, price, amount
            item_pattern = r'([A-Za-z\s]+)\s+(\d+)\s+[₹Rs]?\s*([\d.]+)'
            match = re.search(item_pattern, line)
            if match:
                items.append({
                    "desc": match.group(1).strip(),
                    "qty": int(match.group(2)),
                    "unit_price": float(match.group(3))
                })
        
        return items[:10]  # Limit to 10 items

