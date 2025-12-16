from fastapi import FastAPI, UploadFile, File
from typing import List
import uuid
import datetime
import io

import pdfplumber
import camelot
import fitz  # pymupdf
import pytesseract
from PIL import Image

app = FastAPI(title="PDF Extraction Pipeline")

# -----------------------------
# Helpers
# -----------------------------

def extract_text(pdf_path):
    pages_text = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            pages_text[i] = text.strip() if text else ""
    return pages_text


def extract_tables(pdf_path):
    tables_by_page = {}
    try:
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
        for idx, table in enumerate(tables):
            page = table.page
            tables_by_page.setdefault(page, []).append({
                "table_id": f"table_{page}_{idx+1}",
                "rows": table.df.values.tolist(),
                "source": "camelot-stream"
            })
    except Exception as e:
        print("Camelot error:", e)
    return tables_by_page


def extract_images_ocr(pdf_path):
    images_by_page = {}
    doc = fitz.open(pdf_path)

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        images_by_page[page_number] = []

        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            image = Image.open(io.BytesIO(image_bytes))
            ocr_text = pytesseract.image_to_string(image).strip()

            images_by_page[page_number].append({
                "image_id": f"p{page_number}_img{img_index+1}",
                "ocr_text": ocr_text,
                "source": "pymupdf+tesseract"
            })

    return images_by_page


# -----------------------------
# API
# -----------------------------

@app.post("/extract")
async def extract_pdfs(files: List[UploadFile] = File(...)):
    responses = []

    for file in files:
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        pdf_bytes = await file.read()

        tmp_path = f"/tmp/{file_id}.pdf"
        with open(tmp_path, "wb") as f:
            f.write(pdf_bytes)

        text_data = extract_text(tmp_path)
        table_data = extract_tables(tmp_path)
        image_data = extract_images_ocr(tmp_path)

        pages = []
        total_pages = max(
            len(text_data),
            len(table_data) if table_data else 0,
            len(image_data) if image_data else 0
        )

        for page_num in range(1, total_pages + 1):
            pages.append({
                "page_number": page_num,
                "content": {
                    "text": text_data.get(page_num, ""),
                    "tables": table_data.get(page_num, []),
                    "images": image_data.get(page_num, [])
                }
            })

        responses.append({
            "file_id": file_id,
            "filename": file.filename,
            "total_pages": total_pages,
            "pages": pages
        })

    return {
        "status": "success",
        "extracted_at": datetime.datetime.utcnow().isoformat(),
        "documents": responses,
        "metadata": {
            "pipeline": [
                "pdfplumber (text)",
                "camelot-stream (tables)",
                "pymupdf + tesseract (image OCR)"
            ],
            "images_saved": False
        }
    }
