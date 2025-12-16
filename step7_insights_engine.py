"""
STEP 7 — INSIGHTS ENGINE (LLM-Powered Analysis)
Analyzes extracted data and provides intelligent insights and recommendations
"""
import os
from dotenv import load_dotenv
from typing import List, Dict

try:
    from groq import Groq
except Exception:
    Groq = None  # Optional dependency; fallback will be used

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"
client = None
if GROQ_API_KEY and Groq is not None:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Groq init error, using fallback insights: {e}")


class InsightsEngine:
    """Generate intelligent insights and recommendations using LLM"""

    def generate_insights(self, events: List[Dict], risks: List[Dict], alerts: List[Dict], sector: str, text: str) -> Dict:
        """Generate comprehensive insights and recommendations"""
        events_summary = self._summarize_events(events, sector)
        risks_summary = self._summarize_risks(risks)
        status = self._determine_status(risks, alerts)
        return self._llm_analyze(events_summary, risks_summary, alerts, sector, text, status, risks)

    def _summarize_events(self, events: List[Dict], sector: str) -> str:
        if not events:
            return "No structured data extracted from the document."
        summary_parts = []
        for event in events[:10]:
            event_type = event.get("type", "unknown")
            if sector == "finance" and event_type == "invoice":
                summary_parts.append(
                    f"Invoice {event.get('invoice_no', 'N/A')}: "
                    f"Total ₹{event.get('total', 0)}, "
                    f"GST {event.get('gst_percent', 0)}%, "
                    f"Vendor: {event.get('vendor', 'Unknown')}"
                )
            elif sector == "healthcare" and event_type == "lab_result":
                summary_parts.append(
                    f"Lab Test: {event.get('test', 'N/A')} = {event.get('value', 'N/A')} "
                    f"{event.get('units', '')} (Ref: {event.get('ref_range', 'N/A')})"
                )
            elif sector == "healthcare" and event_type == "medication":
                summary_parts.append(
                    f"Medication: {event.get('name', 'N/A')} "
                    f"{event.get('dose', 'N/A')} {event.get('frequency', '')}"
                )
            elif sector == "agriculture":
                summary_parts.append(
                    f"{event.get('type', 'N/A').replace('_', ' ').title()}: "
                    f"{event.get('value', 'N/A')} {event.get('units', '')}"
                )
            else:
                summary_parts.append(f"{event_type}: {str(event)[:100]}")
        return "\n".join(summary_parts) if summary_parts else "No events to summarize."

    def _summarize_risks(self, risks: List[Dict]) -> str:
        if not risks:
            return "No risks detected."
        risk_parts = []
        for risk in risks:
            severity = risk.get("severity", "medium")
            risk_parts.append(
                f"[{severity.upper()}] {risk.get('risk', 'Unknown risk')}: "
                f"{risk.get('explanation', '')}"
            )
        return "\n".join(risk_parts)

    def _determine_status(self, risks: List[Dict], alerts: List[Dict]) -> str:
        if not risks and not alerts:
            return "ok"
        high_severity = any(r.get("severity") in ["high", "critical"] for r in risks + alerts)
        if high_severity:
            return "critical"
        if risks or alerts:
            return "warning"
        return "ok"

    def _llm_analyze(self, events_summary: str, risks_summary: str, alerts: List[Dict], sector: str, text: str, status: str, risks: List[Dict]) -> Dict:
        if status == "ok":
            prompt = f"""Analyze this {sector} document and provide a brief summary.

Extracted Data:
{events_summary}

Document Status: Everything looks good, no issues detected.

Provide:
1. A concise summary (2-3 sentences) of what this document contains
2. Key findings (3-5 bullet points)
3. No recommendations needed since everything is OK

Format your response as JSON:
{{
  "summary": "...",
  "key_findings": ["...", "..."],
  "recommendations": []
}}"""
        else:
            alerts_text = "\n".join([f"- {a.get('title', '')}: {a.get('reason', '')}" for a in alerts[:5]])
            prompt = f"""Analyze this {sector} document and provide insights.

Extracted Data:
{events_summary}

Detected Issues:
{risks_summary}

Alerts:
{alerts_text}

Document Status: {status.upper()} - Issues detected

Provide:
1. A clear summary (2-3 sentences) explaining what's going on
2. Key findings (3-5 bullet points)
3. Actionable recommendations (3-5 items) to address the issues

Format your response as JSON:
{{
  "summary": "...",
  "key_findings": ["...", "..."],
  "recommendations": ["...", "..."]
}}"""

        if client is None:
            return self._fallback_insights(status, events_summary, risks, alerts, sector)

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert document analyst. Always respond with valid JSON only, no markdown, no code blocks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            import json, re
            content = response.choices[0].message.content.strip()
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            result = json.loads(content)
            return {
                "summary": result.get("summary", "Document analyzed successfully."),
                "status": status,
                "key_findings": result.get("key_findings", []),
                "recommendations": result.get("recommendations", []) if status != "ok" else []
            }
        except Exception as e:
            print(f"LLM insights error: {e}")
            return self._fallback_insights(status, events_summary, risks, alerts, sector)

    def _fallback_insights(self, status: str, events_summary: str, risks: List[Dict], alerts: List[Dict], sector: str) -> Dict:
        event_count = len(events_summary.split("\n")) if events_summary else 0
        if status == "ok":
            return {
                "summary": f"Document processed successfully. Extracted {event_count} items from {sector} document. Everything looks good.",
                "status": "ok",
                "key_findings": ["Document processed without issues", "All data extracted successfully", f"Classified as {sector} sector"],
                "recommendations": []
            }
        risk_list = [r.get("risk", "Risk detected") for r in risks[:5]] if risks else []
        rec_list = []
        for a in alerts[:3]:
            if a.get("recommended_actions"):
                rec_list.extend(a.get("recommended_actions", [])[:1])
        return {
            "summary": f"Document processed with {len(risks)} risk(s) detected. Review the alerts for details.",
            "status": status,
            "key_findings": risk_list if risk_list else ["Issues detected - review alerts"],
            "recommendations": rec_list if rec_list else ["Review the document", "Check alerts for details"]
        }
