"""
STEP 2 — PREPROCESSING (OCR / Parsing)
Converts ANY document into clean text using existing extractors
"""
import os
import io
from pathlib import Path
from typing import Dict, Any
from langdetect import detect, LangDetectException

# Import existing extractors from extractors directory
from extractors.pdf_extract import extract_text, extract_tables, extract_images_ocr
from extractors.excel_extract import extract_excel
from extractors.docs_extract import extract_docx
from extractors.image_extract import image_to_cv, extract_text as extract_image_text, extract_tables as extract_image_tables


def detect_file_type(filename: str, file_bytes: bytes) -> str:
    """Detect file type from extension and magic bytes"""
    ext = Path(filename).suffix.lower()
    
    # Check magic bytes for more accuracy
    if file_bytes[:4] == b'%PDF':
        return "pdf"
    elif ext in ['.pdf']:
        return "pdf"
    elif ext in ['.xlsx', '.xls']:
        return "excel"
    elif ext in ['.docx', '.doc']:
        return "docx"
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
        return "image"
    elif ext in ['.txt', '.log']:
        return "text"
    else:
        return "unknown"


def normalize_text(text: str) -> str:
    """Clean and normalize extracted text"""
    # Remove excessive whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)


def detect_language(text: str) -> str:
    """Detect language of text"""
    try:
        if not text or len(text.strip()) < 10:
            return "unknown"
        return detect(text)
    except LangDetectException:
        return "unknown"


def preprocess_file(file_id: str, file_bytes: bytes, filename: str, stored_path: str) -> dict:
    """
    Preprocess file: extract text, detect language, normalize
    
    Returns:
    {
        "file_id": "file_123",
        "text": "Clean extracted text ...",
        "language": "en",
        "metadata": {...}
    }
    """
    file_type = detect_file_type(filename, file_bytes)
    metadata = {
        "file_type": file_type,
        "filename": filename,
        "file_size": len(file_bytes)
    }
    
    extracted_text = ""
    structured_data = {}
    
    # Route to appropriate extractor
    if file_type == "pdf":
        # Use existing PDF extractor
        tmp_path = f"/tmp/{file_id}.pdf"
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)
        
        text_data = extract_text(tmp_path)
        # Combine all pages
        extracted_text = "\n\n".join([text for text in text_data.values() if text])
        structured_data = {
            "pages": len(text_data),
            "tables": extract_tables(tmp_path),
            "images": extract_images_ocr(tmp_path)
        }
        
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    
    elif file_type == "excel":
        result = extract_excel(file_bytes)
        # Extract text from tables
        text_parts = []
        for page in result.get("document", {}).get("pages", []):
            for table in page.get("content", {}).get("tables", []):
                # Convert table to text
                if table.get("columns"):
                    text_parts.append(" | ".join(table["columns"]))
                for row in table.get("rows", []):
                    text_parts.append(" | ".join([str(cell) for cell in row]))
        extracted_text = "\n".join(text_parts)
        structured_data = result.get("document", {})
    
    elif file_type == "docx":
        result = extract_docx(file_bytes)
        # Combine text blocks
        text_parts = []
        for page in result.get("document", {}).get("pages", []):
            for block in page.get("content", {}).get("text_blocks", []):
                text_parts.append(block.get("text", ""))
        extracted_text = "\n".join(text_parts)
        structured_data = result.get("document", {})
    
    elif file_type == "image":
        # Use image extractor
        try:
            image_cv = image_to_cv(file_bytes)
            extracted_text = extract_image_text(image_cv)
            structured_data = {
                "tables": extract_image_tables(image_cv)
            }
        except Exception as e:
            print(f"Image extraction error: {e}")
            extracted_text = ""
            structured_data = {}
    
    elif file_type == "text":
        # Plain text file
        try:
            extracted_text = file_bytes.decode('utf-8')
        except:
            extracted_text = file_bytes.decode('latin-1', errors='ignore')
    
    else:
        # Unknown type - try OCR as fallback
        try:
            from PIL import Image
            import pytesseract
            image = Image.open(io.BytesIO(file_bytes))
            extracted_text = pytesseract.image_to_string(image)
        except:
            extracted_text = ""
    
    # Normalize text
    extracted_text = normalize_text(extracted_text)
    
    # Detect language
    language = detect_language(extracted_text)
    
    metadata.update({
        "text_length": len(extracted_text),
        "has_structured_data": bool(structured_data)
    })
    
    return {
        "file_id": file_id,
        "text": extracted_text,
        "language": language,
        "metadata": metadata,
        "structured_data": structured_data
    }

