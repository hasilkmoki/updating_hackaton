"""
LLM-based Extraction Helper
Uses Groq LLM as fallback for complex extraction when regex fails
"""
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
import json
import re

try:
    from groq import Groq
except Exception:
    Groq = None

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"
client = None
if GROQ_API_KEY and Groq is not None:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Groq init error: {e}")


class LLMExtractor:
    """LLM-based extraction for complex cases"""
    
    @staticmethod
    def extract_structured_data(text: str, schema: Dict, sector: str, max_tokens: int = 1000) -> Dict:
        """
        Extract structured data using LLM based on schema
        
        Args:
            text: Document text
            schema: Expected output schema with field descriptions
            sector: Sector name (healthcare, finance, etc.)
            max_tokens: Max tokens for response
        
        Returns:
            Extracted structured data matching schema
        """
        if client is None:
            return {}
        
        # Build schema description
        schema_desc = "\n".join([f"- {k}: {v}" for k, v in schema.items()])
        
        prompt = f"""Extract structured information from this {sector} document.

Expected fields:
{schema_desc}

Document text (first 3000 chars):
{text[:3000]}

Respond with ONLY valid JSON matching this structure:
{json.dumps({k: None for k in schema.keys()}, indent=2)}

Return null for fields not found. Be precise and accurate."""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise data extraction assistant. Always respond with valid JSON only, no markdown, no code blocks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            result = json.loads(content)
            return result
        except Exception as e:
            print(f"LLM extraction error: {e}")
            return {}
    
    @staticmethod
    def extract_healthcare_events(text: str) -> List[Dict]:
        """Extract healthcare events using LLM"""
        if client is None:
            return []
        
        prompt = f"""Extract all healthcare events from this medical document.

Look for:
1. Lab test results (test name, value, units, reference range, date)
2. Medications (name, dose, frequency, start date)
3. Diagnoses (condition name, date)

Document text (first 3000 chars):
{text[:3000]}

Respond with JSON array of events:
[
  {{
    "type": "lab_result|medication|diagnosis",
    "test": "test name" (for lab_result),
    "value": number (for lab_result),
    "units": "unit" (for lab_result),
    "ref_range": "min-max" (for lab_result),
    "name": "medication name" (for medication),
    "dose": "dose" (for medication),
    "frequency": "frequency" (for medication),
    "condition": "condition name" (for diagnosis),
    "date": "date if found"
  }}
]

Return empty array if nothing found."""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a medical document analysis expert. Always respond with valid JSON array only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            events = json.loads(content)
            if isinstance(events, list):
                return events
            return []
        except Exception as e:
            print(f"LLM healthcare extraction error: {e}")
            return []
    
    @staticmethod
    def extract_finance_events(text: str) -> List[Dict]:
        """Extract finance events using LLM"""
        if client is None:
            return []
        
        prompt = f"""Extract financial information from this document.

Look for:
1. Invoice details (invoice number, date, vendor, amounts, GST, line items)
2. Payment information (amount, date, method)
3. Tax information (GST, GSTIN, tax amounts)

Document text (first 3000 chars):
{text[:3000]}

Respond with JSON:
{{
  "invoice_no": "string or null",
  "date": "string or null",
  "vendor": "string or null",
  "buyer": "string or null",
  "gstin": "string or null",
  "taxable_total": number or null,
  "gst_percent": number or null,
  "gst_amount": number or null,
  "total": number or null,
  "line_items": [{{"desc": "string", "qty": number, "unit_price": number}}] or []
}}

Return null for fields not found."""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a financial document analysis expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            result = json.loads(content)
            return result
        except Exception as e:
            print(f"LLM finance extraction error: {e}")
            return {}

