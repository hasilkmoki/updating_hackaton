"""
STEP 1 — UPLOAD / INGESTION
Handles file upload, storage, and metadata generation
"""
import os
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path

# Storage directory
STORAGE_DIR = Path("storage/files")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def upload_file(file_bytes: bytes, filename: str, uploader: Optional[str] = None) -> dict:
    """
    Upload and store file, generate file_id and metadata
    
    Returns:
    {
        "file_id": "file_123",
        "raw_file": "<stored_path>",
        "meta": {"filename": "report.pdf", "uploaded_at": ...}
    }
    """
    # Generate unique file_id
    file_id = f"file_{uuid.uuid4().hex[:8]}"
    
    # Determine file extension
    file_ext = Path(filename).suffix or ".bin"
    stored_path = STORAGE_DIR / f"{file_id}{file_ext}"
    
    # Save file
    with open(stored_path, "wb") as f:
        f.write(file_bytes)
    
    # Generate metadata
    metadata = {
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat(),
        "uploader": uploader,
        "file_size": len(file_bytes),
        "file_type": file_ext[1:] if file_ext.startswith(".") else file_ext
    }
    
    return {
        "file_id": file_id,
        "raw_file": str(stored_path),
        "meta": metadata
    }


def get_file_path(file_id: str) -> Optional[Path]:
    """Retrieve stored file path by file_id"""
    for file_path in STORAGE_DIR.glob(f"{file_id}.*"):
        return file_path
    return None

