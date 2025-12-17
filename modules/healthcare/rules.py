"""
Healthcare Sector Risk Rules
Comprehensive risk detection: abnormal values, drug interactions, 
missing follow-ups, medication adherence, critical values, trends
"""
from modules.base_rules import BaseRules
from typing import List, Dict
from datetime import datetime, timedelta


class HealthcareRules(BaseRules):
    """Healthcare-specific risk detection"""
    
    def detect_risks(self, events: List[Dict], timeline: List[Dict] = None) -> List[Dict]:
        """Detect comprehensive healthcare risks"""
        risks = []
        timeline = timeline or []
        all_events = events + timeline
        
        # Check for abnormal lab values
        risks.extend(self._check_abnormal_labs(events))
        
        # Check for critical lab values (immediate attention needed)
        risks.extend(self._check_critical_values(events))
        
        # Check for drug interactions
        risks.extend(self._check_drug_interactions(all_events))
        
        # Check for missing follow-ups
        risks.extend(self._check_missing_followups(events, timeline))
        
        # Check for medication adherence issues
        risks.extend(self._check_medication_adherence(all_events))
        
        # Check for trend analysis (worsening conditions)
        risks.extend(self._check_trends(all_events))
        
        # Check for conflicting medications
        risks.extend(self._check_conflicting_medications(all_events))
        
        return risks
    
    def _check_abnormal_labs(self, events: List[Dict]) -> List[Dict]:
        """Check for abnormal lab values with severity assessment"""
        risks = []
        
        for event in events:
            if event.get("type") == "lab_result" and event.get("abnormal"):
                test = event.get("test", "")
                value = event.get("value", 0)
                ref_range = event.get("ref_range", "")
                units = event.get("units", "")
                
                # Determine severity based on how far outside range
                severity = "medium"
                deviation = 0
                
                if "-" in ref_range:
                    try:
                        parts = ref_range.split("-")
                        min_val = float(parts[0].strip())
                        max_val = float(parts[1].strip())
                        mid_val = (min_val + max_val) / 2
                        
                        if value < min_val:
                            deviation = abs(value - min_val) / mid_val
                        elif value > max_val:
                            deviation = abs(value - max_val) / mid_val
                        
                        # High severity if >50% deviation from range
                        if deviation > 0.5:
                            severity = "high"
                        elif deviation > 1.0:
                            severity = "critical"
                    except:
                        pass
                
                # Special cases for critical tests
                test_lower = test.lower()
                if "hba1c" in test_lower and value > 9.0:
                    severity = "high"
                elif "glucose" in test_lower and (value > 200 or value < 50):
                    severity = "high"
                elif "creatinine" in test_lower and value > 2.0:
                    severity = "high"
                
                risks.append({
                    "risk": f"Abnormal {test} value",
                    "severity": severity,
                    "event_ids": [event.get("event_id")],
                    "explanation": f"{test} = {value} {units} is outside normal range ({ref_range}). Deviation: {deviation*100:.1f}%"
                })
        
        return risks
    
    def _check_critical_values(self, events: List[Dict]) -> List[Dict]:
        """Check for critical lab values requiring immediate attention"""
        risks = []
        
        critical_thresholds = {
            "glucose": {"min": 40, "max": 400},
            "hba1c": {"min": 3.0, "max": 12.0},
            "creatinine": {"min": 0.3, "max": 5.0},
            "hemoglobin": {"min": 7.0, "max": 20.0},
            "bp": {"min": 80, "max": 180},  # systolic
        }
        
        for event in events:
            if event.get("type") == "lab_result":
                test = event.get("test", "").lower()
                value = event.get("value", 0)
                
                for crit_test, thresholds in critical_thresholds.items():
                    if crit_test in test:
                        if value < thresholds["min"] or value > thresholds["max"]:
                            risks.append({
                                "risk": f"CRITICAL: {event.get('test')} value requires immediate attention",
                                "severity": "critical",
                                "event_ids": [event.get("event_id")],
                                "explanation": f"{event.get('test')} = {value} is in critical range. Immediate medical attention recommended."
                            })
                        break
        
        return risks
    
    def _check_drug_interactions(self, events: List[Dict]) -> List[Dict]:
        """Check for potential drug interactions - comprehensive list"""
        risks = []
        
        # Extended interaction database (in production, use FDA/medical database)
        interaction_pairs = [
            # High severity interactions
            (("metformin", "insulin"), "high", "May cause severe hypoglycemia"),
            (("aspirin", "warfarin"), "high", "Increased bleeding risk"),
            (("aspirin", "ibuprofen"), "medium", "May reduce aspirin's cardioprotective effects"),
            (("ace inhibitor", "potassium"), "high", "Risk of hyperkalemia"),
            (("digoxin", "diuretics"), "high", "Risk of digoxin toxicity"),
            (("warfarin", "antibiotics"), "high", "Increased bleeding risk"),
            (("statins", "grapefruit"), "medium", "May increase statin levels"),
            (("beta blocker", "calcium channel blocker"), "medium", "May cause bradycardia"),
            (("lithium", "diuretics"), "high", "Risk of lithium toxicity"),
            (("maoi", "ssri"), "critical", "Serotonin syndrome risk"),
        ]
        
        meds = [e for e in events if e.get("type") == "medication"]
        med_names = [m.get("name", "").lower() for m in meds]
        
        for (med1, med2), severity, reason in interaction_pairs:
            # Check if both medications are present
            med1_found = any(med1 in name for name in med_names)
            med2_found = any(med2 in name for name in med_names)
            
            if med1_found and med2_found:
                event_ids = [m.get("event_id") for m in meds 
                           if med1 in m.get("name", "").lower() or med2 in m.get("name", "").lower()]
                risks.append({
                    "risk": f"Drug interaction: {med1} + {med2}",
                    "severity": severity,
                    "event_ids": event_ids,
                    "explanation": f"{reason}. Concurrent use of {med1} and {med2} detected."
                })
        
        return risks
    
    def _check_conflicting_medications(self, events: List[Dict]) -> List[Dict]:
        """Check for medications that treat opposite conditions"""
        risks = []
        
        meds = [e for e in events if e.get("type") == "medication"]
        med_names = [m.get("name", "").lower() for m in meds]
        
        # Medications that might conflict
        conflicts = [
            (("antihypertensive", "stimulant"), "Treating opposite conditions"),
            (("anticoagulant", "hemostatic"), "Opposing effects on blood clotting"),
        ]
        
        for (med_type1, med_type2), reason in conflicts:
            has_type1 = any(med_type1 in name for name in med_names)
            has_type2 = any(med_type2 in name for name in med_names)
            
            if has_type1 and has_type2:
                event_ids = [m.get("event_id") for m in meds]
                risks.append({
                    "risk": f"Conflicting medications detected",
                    "severity": "medium",
                    "event_ids": event_ids,
                    "explanation": f"{reason}. Review medication list."
                })
        
        return risks
    
    def _check_missing_followups(self, events: List[Dict], timeline: List[Dict]) -> List[Dict]:
        """Check for missing follow-up tests for any diagnosis"""
        risks = []
        
        # Get all diagnoses from current events and timeline
        all_diagnoses = [e for e in events + timeline if e.get("type") == "diagnosis"]
        
        if not all_diagnoses:
            return risks
        
        # Mapping of conditions to recommended follow-up tests
        # This can be extended for any health condition
        condition_followups = {
            "diabetes": ["hba1c", "glucose", "blood sugar"],
            "hypertension": ["bp", "blood pressure"],
            "anemia": ["hemoglobin", "hgb", "rbc"],
            "thyroid": ["tsh", "t3", "t4"],
            "kidney": ["creatinine", "egfr", "bun"],
            "liver": ["alt", "ast", "bilirubin"],
            "heart": ["ecg", "echocardiogram", "troponin"],
            "cholesterol": ["cholesterol", "ldl", "hdl", "triglycerides"]
        }
        
        # Check each diagnosis for missing follow-ups
        for diagnosis_event in all_diagnoses:
            condition = diagnosis_event.get("condition", "").lower()
            if not condition:
                continue
            
            # Find matching follow-up tests for this condition
            recommended_tests = []
            for cond_key, test_list in condition_followups.items():
                if cond_key in condition:
                    recommended_tests.extend(test_list)
            
            # If no specific mapping, check for general lab results
            if not recommended_tests:
                # Generic check: if diagnosis exists, should have some recent lab results
                recent_labs = [e for e in timeline[-10:] if e.get("type") == "lab_result"]
                if not recent_labs:
                    diagnosis_event_ids = [diagnosis_event.get("event_id")] if diagnosis_event.get("event_id") else []
                    risks.append({
                        "risk": f"Missing follow-up tests for {condition}",
                        "severity": "medium",
                        "event_ids": diagnosis_event_ids,
                        "explanation": f"{condition.capitalize()} diagnosis found but no recent lab results in timeline"
                    })
                continue
            
            # Check if recommended tests are present in recent timeline
            recent_labs = [e for e in timeline[-10:] if e.get("type") == "lab_result"]
            recent_test_names = [e.get("test", "").lower() for e in recent_labs]
            
            missing_tests = []
            for test in recommended_tests:
                if not any(test in test_name for test_name in recent_test_names):
                    missing_tests.append(test)
            
            if missing_tests:
                diagnosis_event_ids = [diagnosis_event.get("event_id")] if diagnosis_event.get("event_id") else []
                test_list = ", ".join([t.upper() for t in missing_tests[:3]])  # Limit to 3 tests
                risks.append({
                    "risk": f"Missing follow-up tests for {condition}",
                    "severity": "medium",
                    "event_ids": diagnosis_event_ids,
                    "explanation": f"{condition.capitalize()} diagnosis found but missing recommended follow-up tests: {test_list}"
                })
        
        return risks
    
    def _check_medication_adherence(self, events: List[Dict]) -> List[Dict]:
        """Check for medication adherence issues based on timeline"""
        risks = []
        
        # Get all medications from timeline
        meds = [e for e in events if e.get("type") == "medication"]
        
        if not meds:
            return risks
        
        # Check for medications that should be taken together but aren't
        # Example: Metformin + Insulin for diabetes
        diabetes_meds = ["metformin", "insulin", "glipizide"]
        has_diabetes_med = any(med.lower() in m.get("name", "").lower() for m in meds for med in diabetes_meds)
        
        if has_diabetes_med:
            # Check if patient has diabetes diagnosis
            has_diabetes_diag = any("diabetes" in str(e).lower() for e in events)
            if not has_diabetes_diag:
                risks.append({
                    "risk": "Medication without corresponding diagnosis",
                    "severity": "medium",
                    "event_ids": [m.get("event_id") for m in meds],
                    "explanation": "Diabetes medications found but no diabetes diagnosis recorded"
                })
        
        return risks
    
    def _check_trends(self, events: List[Dict]) -> List[Dict]:
        """Check for worsening trends in lab values"""
        risks = []
        
        # Group lab results by test type
        lab_results = [e for e in events if e.get("type") == "lab_result"]
        
        # Track values over time for key tests
        test_values = {}
        for lab in lab_results:
            test = lab.get("test", "").lower()
            value = lab.get("value", 0)
            date = lab.get("date")
            
            if test not in test_values:
                test_values[test] = []
            
            test_values[test].append({
                "value": value,
                "date": date,
                "event_id": lab.get("event_id")
            })
        
        # Check for worsening trends
        critical_tests = ["hba1c", "glucose", "creatinine", "cholesterol"]
        
        for test in critical_tests:
            if test in test_values and len(test_values[test]) >= 2:
                values = sorted(test_values[test], key=lambda x: x.get("date") or "")
                
                # Check if values are increasing (worsening)
                if len(values) >= 2:
                    recent = values[-1]["value"]
                    previous = values[-2]["value"]
                    
                    # Calculate percentage change
                    if previous > 0:
                        change_pct = ((recent - previous) / previous) * 100
                        
                        # Alert if significant worsening (>20% increase for most tests)
                        if change_pct > 20:
                            risks.append({
                                "risk": f"Worsening trend: {test.upper()}",
                                "severity": "medium",
                                "event_ids": [values[-1]["event_id"]],
                                "explanation": f"{test.upper()} increased by {change_pct:.1f}% ({previous:.1f} → {recent:.1f}). Trend indicates worsening condition."
                            })
        
        return risks

