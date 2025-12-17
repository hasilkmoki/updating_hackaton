"""
Agriculture Risk Rules
Comprehensive risk detection: soil moisture, temperature, 
pest/disease, nutrient deficiency, irrigation issues
"""
from modules.base_rules import BaseRules
from typing import List, Dict
from datetime import datetime, timedelta


class AgricultureRules(BaseRules):
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect comprehensive agriculture risks"""
        risks = []
        timeline = timeline or []
        all_events = events + timeline
        
        # Soil and water risks
        risks.extend(self._check_soil_moisture(events))
        risks.extend(self._check_soil_ph(events))
        risks.extend(self._check_irrigation_issues(all_events))
        
        # Climate risks
        risks.extend(self._check_temperature_stress(events))
        risks.extend(self._check_rainfall_issues(events))
        
        # Crop health risks
        risks.extend(self._check_pest_disease(events))
        risks.extend(self._check_nutrient_deficiency(events))
        
        # NDVI and crop growth
        risks.extend(self._check_ndvi_health(events, timeline))
        
        return risks
    
    def _check_soil_moisture(self, events: List[Dict]) -> List[Dict]:
        """Check soil moisture levels"""
        risks = []
        for event in events:
            if event.get("type") == "soil_moisture":
                value = event.get("value", 100)
                if value < 15:
                    risks.append({
                        "risk": "Critical: Very low soil moisture",
                        "severity": "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Soil moisture {value}% is critically low. Immediate irrigation required."
                    })
                elif value < 25:
                    risks.append({
                        "risk": "Low soil moisture",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Soil moisture {value}% is below optimal threshold (25-40%)"
                    })
                elif value > 80:
                    risks.append({
                        "risk": "Excessive soil moisture",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Soil moisture {value}% is too high. Risk of waterlogging."
                    })
        return risks
    
    def _check_soil_ph(self, events: List[Dict]) -> List[Dict]:
        """Check soil pH levels"""
        risks = []
        for event in events:
            if event.get("type") == "soil_ph":
                ph = event.get("value", 7.0)
                if ph < 5.5:
                    risks.append({
                        "risk": "Acidic soil pH",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Soil pH {ph} is too acidic. Optimal range: 6.0-7.5. Consider liming."
                    })
                elif ph > 8.0:
                    risks.append({
                        "risk": "Alkaline soil pH",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Soil pH {ph} is too alkaline. Optimal range: 6.0-7.5."
                    })
        return risks
    
    def _check_temperature_stress(self, events: List[Dict]) -> List[Dict]:
        """Check for temperature stress"""
        risks = []
        for event in events:
            if event.get("type") == "temperature":
                temp = event.get("value", 25)
                if temp > 40:
                    risks.append({
                        "risk": "High temperature stress",
                        "severity": "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Temperature {temp}°C is very high. Risk of heat stress to crops."
                    })
                elif temp < 5:
                    risks.append({
                        "risk": "Low temperature / Frost risk",
                        "severity": "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Temperature {temp}°C is very low. Risk of frost damage."
                    })
        return risks
    
    def _check_rainfall_issues(self, events: List[Dict]) -> List[Dict]:
        """Check rainfall patterns"""
        risks = []
        for event in events:
            if event.get("type") == "rainfall":
                rainfall = event.get("value", 0)
                if rainfall > 100:  # mm in a day
                    risks.append({
                        "risk": "Heavy rainfall / Flood risk",
                        "severity": "high",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"Heavy rainfall {rainfall}mm detected. Risk of waterlogging and crop damage."
                    })
        return risks
    
    def _check_pest_disease(self, events: List[Dict]) -> List[Dict]:
        """Check for pest and disease detection"""
        risks = []
        for event in events:
            if event.get("type") == "pest_detection":
                pest = event.get("pest", "")
                risks.append({
                    "risk": f"Pest detected: {pest}",
                    "severity": "high",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"{pest.capitalize()} detected in field. Immediate pest control action required."
                })
            elif event.get("type") == "disease_detection":
                disease = event.get("disease", "")
                risks.append({
                    "risk": f"Disease detected: {disease}",
                    "severity": "high",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"{disease.capitalize()} detected in field. Apply appropriate fungicide/pesticide."
                })
        return risks
    
    def _check_nutrient_deficiency(self, events: List[Dict]) -> List[Dict]:
        """Check for nutrient deficiencies"""
        risks = []
        nutrient_thresholds = {
            "nitrogen": {"min": 20, "max": 50},
            "phosphorus": {"min": 10, "max": 30},
            "potassium": {"min": 15, "max": 40},
        }
        
        for event in events:
            if event.get("type", "").startswith("nutrient_"):
                nutrient = event.get("nutrient", "")
                value = event.get("value", 0)
                threshold = nutrient_thresholds.get(nutrient)
                
                if threshold and value < threshold["min"]:
                    risks.append({
                        "risk": f"Low {nutrient} levels",
                        "severity": "medium",
                        "event_ids": [event.get("event_id")],
                        "explanation": f"{nutrient.capitalize()} level {value} ppm is below optimal ({threshold['min']}-{threshold['max']} ppm). Consider fertilization."
                    })
        return risks
    
    def _check_irrigation_issues(self, events: List[Dict]) -> List[Dict]:
        """Check irrigation patterns"""
        risks = []
        # Check if irrigation is needed but not done
        recent_moisture = [e for e in events if e.get("type") == "soil_moisture"]
        recent_irrigation = [e for e in events if e.get("type") == "irrigation"]
        
        if recent_moisture and not recent_irrigation:
            low_moisture = [e for e in recent_moisture if e.get("value", 100) < 25]
            if low_moisture:
                risks.append({
                    "risk": "Irrigation needed but not detected",
                    "severity": "medium",
                    "event_ids": [e.get("event_id") for e in low_moisture],
                    "explanation": "Low soil moisture detected but no recent irrigation activity. Schedule irrigation."
                })
        return risks
    
    def _check_ndvi_health(self, events: List[Dict], timeline: List[Dict]) -> List[Dict]:
        """Check NDVI values for crop health"""
        risks = []
        all_ndvi = [e for e in events + timeline if e.get("type") == "ndvi"]
        
        for event in all_ndvi:
            ndvi = event.get("value", 0)
            if ndvi < 0.2:
                risks.append({
                    "risk": "Poor crop health (Low NDVI)",
                    "severity": "high",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"NDVI {ndvi:.2f} indicates poor crop health or bare soil. Optimal: 0.3-0.8"
                })
            elif ndvi < 0.3:
                risks.append({
                    "risk": "Below optimal crop health",
                    "severity": "medium",
                    "event_ids": [event.get("event_id")],
                    "explanation": f"NDVI {ndvi:.2f} is below optimal range. Check for nutrient deficiency or stress."
                })
        
        # Check for declining NDVI trend
        if len(all_ndvi) >= 2:
            sorted_ndvi = sorted(all_ndvi, key=lambda x: x.get("date") or "")
            recent = sorted_ndvi[-1].get("value", 0)
            previous = sorted_ndvi[-2].get("value", 0)
            
            if previous > 0 and (recent - previous) / previous < -0.15:  # 15% decline
                risks.append({
                    "risk": "Declining crop health trend",
                    "severity": "medium",
                    "event_ids": [sorted_ndvi[-1].get("event_id")],
                    "explanation": f"NDVI declined from {previous:.2f} to {recent:.2f}. Investigate cause (pest, disease, stress)."
                })
        
        return risks

