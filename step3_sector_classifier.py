"""
STEP 3 — SECTOR CLASSIFICATION (Router Agent)
Uses Groq LLM to classify document sector
"""
import os
from dotenv import load_dotenv

try:
    from groq import Groq
except Exception:
    Groq = None  # Groq SDK optional; fall back to keyword routing

load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"
client = None
if GROQ_API_KEY and Groq is not None:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Groq init error, falling back to keyword routing: {e}")

SECTORS = [
    "healthcare",
    "finance",
    "agriculture",
    "logistics",
    "government",
    "kirana"
]


def classify_sector(text: str, metadata: dict = None) -> dict:
    """
    Classify document sector using Groq LLM
    
    Returns:
    {
        "sector": "finance",
        "confidence": 0.93
    }
    """
    if not text or len(text.strip()) < 10:
        return {
            "sector": "unknown",
            "confidence": 0.0
        }
    
    # Build classification prompt
    prompt = f"""Analyze the following document text and classify it into ONE of these sectors:
- healthcare (medical reports, lab results, prescriptions, diagnoses)
- finance (invoices, receipts, GST documents, bookkeeping)
- agriculture (crop data, soil sensors, satellite data, farming notes)
- logistics (shipments, GPS logs, delivery documents, supply chain)
- government (applications, certificates, compliance documents, renewals)
- kirana (small retailer bills, shop inventory, simple invoices)

Document text (first 2000 chars):
{text[:2000]}

Respond with ONLY the sector name in lowercase, nothing else."""

    # If no Groq client, use keyword fallback immediately
    if client is None:
        sector = _keyword_classify(text)
        return {"sector": sector, "confidence": _calculate_confidence(text, sector)}

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a document classification expert. Respond with only the sector name."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        sector = response.choices[0].message.content.strip().lower()
        
        # Validate sector
        if sector not in SECTORS:
            # Fallback: keyword-based classification
            sector = _keyword_classify(text)
        
        # Calculate confidence (simple heuristic - can be improved)
        confidence = _calculate_confidence(text, sector)
        
        return {
            "sector": sector,
            "confidence": confidence
        }
    
    except Exception as e:
        print(f"Groq API error: {e}")
        # Fallback to keyword-based
        sector = _keyword_classify(text)
        return {
            "sector": sector,
            "confidence": 0.7
        }


def _keyword_classify(text: str) -> str:
    """Fallback keyword-based classification"""
    text_lower = text.lower()
    
    # Healthcare keywords
    healthcare_keywords = ["hba1c", "diagnosis", "prescription", "medication", "lab result", 
                          "patient", "doctor", "hospital", "test", "blood", "sugar"]
    if any(kw in text_lower for kw in healthcare_keywords):
        return "healthcare"
    
    # Finance keywords
    finance_keywords = ["invoice", "gst", "tax", "receipt", "payment", "vendor", 
                       "amount", "total", "bill", "invoice no"]
    if any(kw in text_lower for kw in finance_keywords):
        return "finance"
    
    # Agriculture keywords
    agriculture_keywords = ["soil", "moisture", "crop", "ndvi", "irrigation", 
                           "field", "harvest", "fertilizer"]
    if any(kw in text_lower for kw in agriculture_keywords):
        return "agriculture"
    
    # Logistics keywords
    logistics_keywords = ["shipment", "delivery", "gps", "eta", "tracking", 
                         "logistics", "transport", "route"]
    if any(kw in text_lower for kw in logistics_keywords):
        return "logistics"
    
    # Government keywords
    government_keywords = ["application", "certificate", "renewal", "deadline", 
                         "compliance", "registration", "license"]
    if any(kw in text_lower for kw in government_keywords):
        return "government"
    
    # Kirana keywords (simple bills, shop-related)
    kirana_keywords = ["shop", "store", "retailer", "kirana", "daily", "groceries"]
    if any(kw in text_lower for kw in kirana_keywords):
        return "kirana"
    
    return "finance"  # Default fallback


def _calculate_confidence(text: str, sector: str) -> float:
    """Calculate confidence score based on keyword matches"""
    text_lower = text.lower()
    
    sector_keywords = {
        "healthcare": ["hba1c", "diagnosis", "prescription", "medication", "lab"],
        "finance": ["invoice", "gst", "tax", "receipt", "payment"],
        "agriculture": ["soil", "moisture", "crop", "ndvi", "irrigation"],
        "logistics": ["shipment", "delivery", "gps", "eta", "tracking"],
        "government": ["application", "certificate", "renewal", "deadline"],
        "kirana": ["shop", "store", "retailer", "kirana", "bill"]
    }
    
    keywords = sector_keywords.get(sector, [])
    matches = sum(1 for kw in keywords if kw in text_lower)
    
    # Confidence based on keyword matches
    if matches >= 3:
        return 0.9
    elif matches >= 2:
        return 0.8
    elif matches >= 1:
        return 0.7
    else:
        return 0.6
