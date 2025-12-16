from fastapi import FastAPI, UploadFile, File
import pandas as pd
import uuid
import io

app = FastAPI(title="Excel Extractor")

def extract_excel(file_bytes: bytes):
    file_id = f"xls_{uuid.uuid4().hex[:8]}"
    sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)

    pages = []

    for idx, (sheet_name, df) in enumerate(sheets.items(), start=1):
        df = df.fillna("")

        pages.append({
            "page_number": idx,
            "sheet_name": sheet_name,
            "content": {
                "tables": [
                    {
                        "table_id": f"table_{idx}",
                        "columns": list(df.columns),
                        "rows": df.values.tolist()
                    }
                ]
            }
        })

    return {
        "status": "success",
        "document": {
            "file_id": file_id,
            "document_type": "excel",
            "total_sheets": len(pages),
            "pages": pages
        }
    }


@app.post("/extract/excel")
async def extract_excel_api(file: UploadFile = File(...)):
    file_bytes = await file.read()
    return extract_excel(file_bytes)
