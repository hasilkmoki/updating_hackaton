"""
Logistics Risk Rules
Comprehensive risk detection: temperature breaches, delays, 
route deviations, delivery failures
"""
from modules.base_rules import BaseRules
from typing import List, Dict
from datetime import datetime, timedelta


class LogisticsRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect comprehensive logistics risks"""
        risks = []
        timeline = timeline or []
        all_events = events + timeline
        
        # Temperature monitoring (cold chain)
        risks.extend(self._check_temperature_breaches(events))
        
        # Delivery delays
        risks.extend(self._check_delivery_delays(all_events))
        
        # Delivery failures
        risks.extend(self._check_delivery_failures(events))
        
        # Route issues
        risks.extend(self._check_route_deviations(all_events))
        
        return risks
    
    def _check_temperature_breaches(self, events: List[Dict]) -> List[Dict]:
        """Check for temperature breaches (cold chain)"""
        risks = []
        for event in events:
            if event.get("type") == "temperature":
                temp = event.get("value", 0)
                # Cold chain: typically 2-8°C
                if temp > 8:
                    risks.append({
                        "risk": "Temperature breach - Above threshold",
                        "severity": "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Temperature {temp}°C exceeds cold chain limit (8°C). Product quality may be compromised."
                    })
                elif temp < 2:
                    risks.append({
                        "risk": "Temperature breach - Below threshold",
                        "severity": "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Temperature {temp}°C is below cold chain limit (2°C). Risk of freezing damage."
                    })
        return risks
    
    def _check_delivery_delays(self, events: List[Dict]) -> List[Dict]:
        """Check for delivery delays"""
        risks = []
        shipments = [e for e in events if e.get("type") == "shipment"]
        etas = [e for e in events if e.get("type") == "eta"]
        deliveries = [e for e in events if e.get("type") == "delivery_status" and e.get("status") == "delivered"]
        
        for eta in etas:
            expected_time = eta.get("expected_time")
            if expected_time:
                try:
                    # Parse expected time
                    eta_date = self._parse_datetime(expected_time)
                    if eta_date and (datetime.now() - eta_date).days > 0:
                        # Check if delivered
                        shipment_id = None
                        for ship in shipments:
                            if ship.get("date") == eta.get("date"):
                                shipment_id = ship.get("shipment_id")
                                break
                        
                        delivered = any(d.get("date") == eta.get("date") for d in deliveries)
                        if not delivered:
                            days_delayed = (datetime.now() - eta_date).days
                            risks.append({
                                "risk": f"Delivery delayed - {days_delayed} days overdue",
                                "severity": "high" if days_delayed > 3 else "medium",
                                "event_ids": [eta.get("event_id")],
                                "explanation": f"Expected delivery was {expected_time}, but shipment not yet delivered. Delay: {days_delayed} days."
                            })
                except:
                    pass
        
        return risks
    
    def _check_delivery_failures(self, events: List[Dict]) -> List[Dict]:
        """Check for delivery failures"""
        risks = []
        for event in events:
            if event.get("type") == "delivery_status" and event.get("status") == "failed":
                risks.append({
                    "risk": "Delivery failed",
                    "severity": "high",
                    "event_ids": [event.get("event_id")],
                    "explanation": "Delivery attempt failed. Review reason and reschedule."
                })
        return risks
    
    def _check_route_deviations(self, events: List[Dict]) -> List[Dict]:
        """Check for route deviations using GPS"""
        risks = []
        gps_points = [e for e in events if e.get("type") == "gps"]
        
        if len(gps_points) >= 2:
            # Check if GPS points are moving in expected direction
            # Simplified: check if distance between points is reasonable
            sorted_gps = sorted(gps_points, key=lambda x: x.get("date") or "")
            
            for i in range(1, len(sorted_gps)):
                prev = sorted_gps[i-1]
                curr = sorted_gps[i]
                
                # Calculate distance (simplified)
                lat_diff = abs(curr.get("lat", 0) - prev.get("lat", 0))
                lon_diff = abs(curr.get("lon", 0) - prev.get("lon", 0))
                
                # If GPS hasn't moved much but time has passed, might be stuck
                if lat_diff < 0.001 and lon_diff < 0.001:
                    risks.append({
                        "risk": "Possible route deviation or vehicle stuck",
                        "severity": "medium",
                        "event_ids": [curr.get("event_id")],
                        "explanation": "GPS coordinates show minimal movement. Verify vehicle status."
                    })
        
        return risks
    
    def _parse_datetime(self, time_str: str) -> datetime:
        """Parse datetime string"""
        formats = [
            "%d/%m/%Y %H:%M",
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y",
            "%d-%m-%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except:
                continue
        return None

