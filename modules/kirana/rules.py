"""
Kirana Shop Risk Rules
Comprehensive risk detection: unpaid bills, low stock, 
profit margins, customer credit, inventory management
"""
from modules.base_rules import BaseRules
from typing import List, Dict
from datetime import datetime, timedelta


class KiranaRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect comprehensive kirana shop risks"""
        risks = []
        timeline = timeline or []
        all_events = events + timeline
        
        # Payment risks
        risks.extend(self._check_unpaid_bills(all_events))
        risks.extend(self._check_overdue_payments(all_events))
        
        # Inventory risks
        risks.extend(self._check_low_stock(all_events))
        risks.extend(self._check_stockout_risk(all_events))
        risks.extend(self._check_excess_stock(all_events))
        
        # Financial risks
        risks.extend(self._check_profit_margins(events))
        risks.extend(self._check_customer_credit(all_events))
        
        # Operational risks
        risks.extend(self._check_slow_moving_items(all_events))
        risks.extend(self._check_missing_gst(events))
        
        return risks
    
    def _check_unpaid_bills(self, events: List[Dict]) -> List[Dict]:
        """Check for unpaid bills"""
        risks = []
        for event in events:
            if event.get("type") == "bill":
                paid = event.get("paid")
                if paid is False or (paid is None and not event.get("payment_method")):
                    bill_no = event.get("bill_no", "N/A")
                    amount = event.get("amount", 0)
                    risks.append({
                        "risk": "Unpaid bill",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Bill {bill_no} for ₹{amount:.2f} is unpaid. Follow up with customer."
                    })
        return risks
    
    def _check_overdue_payments(self, events: List[Dict]) -> List[Dict]:
        """Check for overdue payments"""
        risks = []
        for event in events:
            if event.get("type") == "bill" and not event.get("paid"):
                bill_date = event.get("date")
                if bill_date:
                    try:
                        bill_date_obj = self._parse_date(bill_date)
                        if bill_date_obj:
                            days_overdue = (datetime.now() - bill_date_obj).days
                            if days_overdue > 30:
                                bill_no = event.get("bill_no", "N/A")
                                amount = event.get("amount", 0)
                                risks.append({
                                    "risk": f"Overdue payment - {days_overdue} days",
                                    "severity": "high" if days_overdue > 60 else "medium",
                                    "event_ids": [event.get("event_id")],
                                    "explanation": f"Bill {bill_no} for ₹{amount:.2f} is {days_overdue} days overdue. Urgent collection required."
                                })
                    except:
                        pass
        return risks
    
    def _check_low_stock(self, events: List[Dict]) -> List[Dict]:
        """Check for low stock levels"""
        risks = []
        for event in events:
            if event.get("type") == "inventory":
                stock_qty = event.get("stock_quantity", 0)
                item_name = event.get("item_name", "Unknown")
                
                # Low stock threshold (customize per item type)
                threshold = 10  # Default threshold
                
                if stock_qty > 0 and stock_qty <= threshold:
                    risks.append({
                        "risk": f"Low stock: {item_name}",
                        "severity": "medium" if stock_qty <= 5 else "low",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"{item_name} stock is low ({stock_qty} units). Reorder soon to avoid stockout."
                    })
        return risks
    
    def _check_stockout_risk(self, events: List[Dict]) -> List[Dict]:
        """Check for items at risk of stockout"""
        risks = []
        # Get recent sales and current stock
        recent_sales = [e for e in events if e.get("type") == "sale"]
        current_stock = {e.get("item_name"): e.get("stock_quantity", 0) 
                        for e in events if e.get("type") == "inventory"}
        
        # Calculate sales rate
        sales_by_item = {}
        for sale in recent_sales:
            item = sale.get("item_name")
            qty = sale.get("quantity", 0)
            sales_by_item[item] = sales_by_item.get(item, 0) + qty
        
        # Check if stock can cover sales
        for item, stock in current_stock.items():
            avg_daily_sales = sales_by_item.get(item, 0) / 7 if sales_by_item.get(item, 0) > 0 else 0
            if avg_daily_sales > 0 and stock > 0:
                days_remaining = stock / avg_daily_sales
                if days_remaining <= 3:
                    risks.append({
                        "risk": f"Stockout risk: {item}",
                        "severity": "high",
                        "event_ids": [e.get("event_id") for e in events if e.get("type") == "inventory" and e.get("item_name") == item],
                        "explanation": f"{item} will run out in ~{days_remaining:.1f} days based on current sales rate. Reorder immediately."
                    })
        
        return risks
    
    def _check_excess_stock(self, events: List[Dict]) -> List[Dict]:
        """Check for excess/slow-moving stock"""
        risks = []
        for event in events:
            if event.get("type") == "inventory":
                stock_qty = event.get("stock_quantity", 0)
                item_name = event.get("item_name", "Unknown")
                
                # Excess stock threshold (customize per item)
                if stock_qty > 100:  # High threshold
                    risks.append({
                        "risk": f"Excess stock: {item_name}",
                        "severity": "low",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"{item_name} has high stock ({stock_qty} units). Check if it's slow-moving."
                    })
        return risks
    
    def _check_profit_margins(self, events: List[Dict]) -> List[Dict]:
        """Check profit margins on bills"""
        risks = []
        for event in events:
            if event.get("type") == "bill":
                items = event.get("items", [])
                total_amount = event.get("amount", 0)
                
                if items and total_amount > 0:
                    # Estimate profit (simplified - would need purchase cost data)
                    # Assume 20-30% margin is healthy
                    estimated_cost = total_amount * 0.75  # 25% margin assumption
                    estimated_profit = total_amount - estimated_cost
                    margin_pct = (estimated_profit / total_amount) * 100
                    
                    if margin_pct < 15:
                        bill_no = event.get("bill_no", "N/A")
                        risks.append({
                            "risk": f"Low profit margin on bill {bill_no}",
                            "severity": "medium",
                            "event_ids": [event.get("event_id")],
                            "explanation": f"Estimated profit margin is {margin_pct:.1f}% (below 15% threshold). Review pricing."
                        })
        return risks
    
    def _check_customer_credit(self, events: List[Dict]) -> List[Dict]:
        """Check customer credit limits"""
        risks = []
        # Track customer outstanding amounts
        customer_balances = {}
        
        for event in events:
            if event.get("type") == "bill":
                customer = event.get("customer", "Walk-in")
                amount = event.get("amount", 0)
                paid = event.get("paid", False)
                
                if not paid:
                    customer_balances[customer] = customer_balances.get(customer, 0) + amount
        
        # Alert if customer has high outstanding
        credit_limit = 5000  # Default credit limit
        for customer, balance in customer_balances.items():
            if balance > credit_limit:
                risks.append({
                    "risk": f"High customer credit: {customer}",
                    "severity": "high",
                    "event_ids": [],
                    "explanation": f"Customer {customer} has outstanding balance of ₹{balance:.2f} (exceeds limit ₹{credit_limit}). Collect payment."
                })
        
        return risks
    
    def _check_slow_moving_items(self, events: List[Dict]) -> List[Dict]:
        """Check for slow-moving inventory"""
        risks = []
        # Get items with high stock but low sales
        stock_items = {e.get("item_name"): e.get("stock_quantity", 0) 
                      for e in events if e.get("type") == "inventory"}
        sales_items = {e.get("item_name"): e.get("quantity", 0) 
                      for e in events if e.get("type") == "sale"}
        
        for item, stock in stock_items.items():
            sales = sales_items.get(item, 0)
            if stock > 20 and sales < 5:  # High stock, low sales
                risks.append({
                    "risk": f"Slow-moving item: {item}",
                    "severity": "low",
                    "event_ids": [e.get("event_id") for e in events if e.get("type") == "inventory" and e.get("item_name") == item],
                    "explanation": f"{item} has high stock ({stock} units) but low sales ({sales} units). Consider discount or discontinue."
                })
        
        return risks
    
    def _check_missing_gst(self, events: List[Dict]) -> List[Dict]:
        """Check for missing GST in bills"""
        risks = []
        for event in events:
            if event.get("type") == "bill":
                amount = event.get("amount", 0)
                gst_amount = event.get("gst_amount", 0)
                
                # If bill amount > threshold but no GST
                if amount > 5000 and gst_amount == 0:
                    bill_no = event.get("bill_no", "N/A")
                    risks.append({
                        "risk": "Missing GST on bill",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Bill {bill_no} amount ₹{amount:.2f} exceeds ₹5000 but no GST found. Verify GST compliance."
                    })
        
        return risks
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string"""
        if not date_str:
            return None
        
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        return None

