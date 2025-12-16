from fastapi import FastAPI, UploadFile, File
from typing import List
from PIL import Image
import pytesseract
import cv2
import numpy as np
import io
import uuid
from datetime import datetime

app = FastAPI(title="Image Text & Table Extractor")

# ---------- HELPERS ----------

def image_to_cv(image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def extract_text(image_cv):
    text = pytesseract.image_to_string(image_cv)
    return text.strip()


def extract_tables(image_cv):
    """
    Simple OCR-based table extraction.
    Returns rows as list of lists.
    """
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV, 15, 5
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    tables = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 200 and h > 100:  # table-like region
            roi = image_cv[y:y+h, x:x+w]
            text = pytesseract.image_to_string(
                roi, config="--psm 6"
            )

            rows = [
                [cell.strip() for cell in row.split("|") if cell.strip()]
                for row in text.split("\n") if row.strip()
            ]

            if rows:
                tables.append(rows)

    return tables


# ---------- API ----------

@app.post("/extract-images")
async def extract_images(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        file_id = f"img_{uuid.uuid4().hex[:8]}"
        image_bytes = await file.read()
        image_cv = image_to_cv(image_bytes)

        text = extract_text(image_cv)
        tables = extract_tables(image_cv)

        results.append({
            "image_id": file_id,
            "filename": file.filename,
            "content": {
                "text": text,
                "tables": tables
            }
        })

    return {
        "status": "success",
        "total_images": len(results),
        "extracted_at": datetime.utcnow().isoformat(),
        "images": results
    }
