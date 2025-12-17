"""
Kirana Shop Extractor
Comprehensive extraction: bills, inventory, stock levels, 
customer payments, profit margins, daily sales
"""
import re
from typing import Dict, List
from modules.base_extractor import BaseExtractor
from modules.llm_extractor import LLMExtractor


class KiranaExtractor(BaseExtractor):
    def extract(self, text: str, metadata: dict = None) -> dict:
        """Extract kirana shop events - comprehensive"""
        file_id = metadata.get('file_id', 'unknown') if metadata else 'unknown'
        events = []
        
        # Extract bills/invoices
        events.extend(self._extract_bills(text, file_id))
        
        # Extract inventory/stock
        events.extend(self._extract_inventory(text, file_id))
        
        # Extract sales transactions
        events.extend(self._extract_sales(text, file_id))
        
        # Extract customer information
        events.extend(self._extract_customers(text, file_id))
        
        # Extract payments
        events.extend(self._extract_payments(text, file_id))
        
        # Extract stock movements
        events.extend(self._extract_stock_movements(text, file_id))
        
        return {"events": events}
    
    def _extract_bills(self, text: str, file_id: str) -> List[Dict]:
        """Extract bill/invoice information"""
        events = []
        patterns = [
            r'(?:bill|BILL|invoice|INV)[\s#:]+([A-Z0-9\-]+)',
            r'Bill\s*No[:\s]+([A-Z0-9\-]+)',
            r'Receipt[:\s#]+([A-Z0-9\-]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                bill_no = match.group(1)
                
                events.append({
                    "event_id": self.generate_event_id("bill"),
                    "type": "bill",
                    "bill_no": bill_no,
                    "vendor": self._extract_vendor(text),
                    "customer": self._extract_customer_name(text),
                    "amount": self._extract_amount(text),
                    "gst_amount": self._extract_gst_amount(text),
                    "items": self._extract_items(text),
                    "date": self._extract_date(text),
                    "paid": self._check_paid_status(text),
                    "payment_method": self._extract_payment_method(text),
                    "confidence": 0.9,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_inventory(self, text: str, file_id: str) -> List[Dict]:
        """Extract inventory/stock information"""
        events = []
        patterns = [
            r'(?:stock|inventory|qty|quantity)[:\s]+([A-Za-z\s]+)[:\s]+(\d+)',
            r'([A-Za-z\s]+)\s+stock[:\s]+(\d+)',
            r'Item[:\s]+([A-Za-z\s]+)[,\s]+Stock[:\s]+(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                item_name = match.group(1).strip()
                stock_qty = int(match.group(2))
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                
                events.append({
                    "event_id": self.generate_event_id("inv"),
                    "type": "inventory",
                    "item_name": item_name,
                    "stock_quantity": stock_qty,
                    "unit": self._extract_unit(text, match.start()),
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_sales(self, text: str, file_id: str) -> List[Dict]:
        """Extract sales transaction information"""
        events = []
        patterns = [
            r'(?:sold|sale)[:\s]+([A-Za-z\s]+)[:\s]+(\d+)\s*(?:units?|pcs?|kg|g)',
            r'Sales[:\s]+([A-Za-z\s]+)[:\s]+Qty[:\s]+(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                item_name = match.group(1).strip()
                qty = int(match.group(2))
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                
                events.append({
                    "event_id": self.generate_event_id("sale"),
                    "type": "sale",
                    "item_name": item_name,
                    "quantity": qty,
                    "amount": self._extract_item_amount(text, item_name),
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_customers(self, text: str, file_id: str) -> List[Dict]:
        """Extract customer information"""
        events = []
        patterns = [
            r'(?:customer|buyer|purchaser)[:\s]+([A-Z][A-Za-z\s]+)',
            r'Name[:\s]+([A-Z][A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                customer_name = match.group(1).strip()
                # Skip common false positives
                if customer_name.lower() in ["total", "amount", "date", "bill"]:
                    continue
                
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("cust"),
                    "type": "customer",
                    "customer_name": customer_name,
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.8,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_payments(self, text: str, file_id: str) -> List[Dict]:
        """Extract payment information"""
        events = []
        payment_methods = ['cash', 'card', 'upi', 'credit', 'debit']
        
        for method in payment_methods:
            pattern = rf'(?:paid|payment)\s*(?:by|via|through)?\s*{method}[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount = float(match.group(1).replace(",", ""))
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("pay"),
                    "type": "payment",
                    "amount": amount,
                    "payment_method": method,
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_stock_movements(self, text: str, file_id: str) -> List[Dict]:
        """Extract stock movement (purchase/sale)"""
        events = []
        patterns = [
            r'(?:purchased|bought|received)[:\s]+([A-Za-z\s]+)[:\s]+(\d+)',
            r'(?:restocked|reorder)[:\s]+([A-Za-z\s]+)[:\s]+(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                item_name = match.group(1).strip()
                qty = int(match.group(2))
                snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                events.append({
                    "event_id": self.generate_event_id("stock"),
                    "type": "stock_movement",
                    "movement_type": "purchase",
                    "item_name": item_name,
                    "quantity": qty,
                    "date": self._extract_date_near_match(text, match.start()),
                    "confidence": 0.85,
                    "provenance": [self.create_provenance(file_id, snippet=snippet)]
                })
        return events
    
    def _extract_vendor(self, text: str) -> str:
        """Extract vendor/supplier name"""
        patterns = [
            r'(?:from|vendor|supplier)[:\s]+([A-Z][A-Za-z\s&]+)',
            r'^([A-Z][A-Za-z\s]{3,30})\s*(?:STORE|SHOP)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "Unknown"
    
    def _extract_customer_name(self, text: str) -> str:
        """Extract customer name"""
        pattern = r'(?:customer|buyer|to)[:\s]+([A-Z][A-Za-z\s]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else "Walk-in"
    
    def _extract_amount(self, text: str) -> float:
        """Extract total amount"""
        patterns = [
            r'(?:total|amount|grand\s*total)[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)',
            r'[₹Rs]\s*([\d,]+\.?\d*)\s*(?:total|final)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return 0.0
    
    def _extract_gst_amount(self, text: str) -> float:
        """Extract GST amount"""
        pattern = r'GST[:\s]*[₹Rs]?\s*([\d,]+\.?\d*)'
        match = re.search(pattern, text, re.IGNORECASE)
        return float(match.group(1).replace(",", "")) if match else 0.0
    
    def _extract_items(self, text: str) -> List[Dict]:
        """Extract line items from bill"""
        items = []
        lines = text.split('\n')
        for line in lines:
            # Pattern: Item Qty Price
            pattern = r'([A-Za-z\s]+)\s+(\d+)\s+[₹Rs]?\s*([\d.]+)'
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                # Skip totals
                if desc.upper() in ["TOTAL", "SUBTOTAL", "GST", "GRAND TOTAL"]:
                    continue
                items.append({
                    "desc": desc,
                    "qty": int(match.group(2)),
                    "price": float(match.group(3))
                })
        return items[:20]
    
    def _extract_date(self, text: str) -> str:
        """Extract date"""
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _check_paid_status(self, text: str) -> bool:
        """Check if bill is paid"""
        text_lower = text.lower()
        paid_keywords = ['paid', 'payment received', 'settled', 'cleared']
        unpaid_keywords = ['unpaid', 'pending', 'due', 'outstanding']
        
        if any(keyword in text_lower for keyword in paid_keywords):
            return True
        if any(keyword in text_lower for keyword in unpaid_keywords):
            return False
        return None  # Unknown
    
    def _extract_payment_method(self, text: str) -> str:
        """Extract payment method"""
        text_lower = text.lower()
        if 'cash' in text_lower:
            return "cash"
        elif 'card' in text_lower or 'debit' in text_lower or 'credit' in text_lower:
            return "card"
        elif 'upi' in text_lower:
            return "upi"
        return "unknown"
    
    def _extract_unit(self, text: str, position: int) -> str:
        """Extract unit near position"""
        start = max(0, position - 30)
        end = min(len(text), position + 30)
        context = text[start:end].lower()
        
        units = ['kg', 'g', 'l', 'ml', 'pcs', 'units', 'packets', 'boxes']
        for unit in units:
            if unit in context:
                return unit
        return "units"
    
    def _extract_item_amount(self, text: str, item_name: str) -> float:
        """Extract amount for specific item"""
        # Look for item name followed by amount
        pattern = rf'{re.escape(item_name)}[:\s]+[₹Rs]?\s*([\d,]+\.?\d*)'
        match = re.search(pattern, text, re.IGNORECASE)
        return float(match.group(1).replace(",", "")) if match else 0.0
    
    def _extract_date_near_match(self, text: str, position: int) -> str:
        """Extract date near match position"""
        start = max(0, position - 100)
        end = min(len(text), position + 100)
        context = text[start:end]
        
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        return None

