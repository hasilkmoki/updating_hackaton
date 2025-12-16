# Example API Responses

## POST /process - Full Pipeline Response

After uploading a document, you get a complete JSON response with all extracted data, risks, and alerts.

### Example 1: Finance Invoice

**Request:**
```bash
POST /process
Content-Type: multipart/form-data
file: invoice.pdf
entity_id: entity_123 (optional)
```

**Response:**
```json
{
  "status": "success",
  "file_id": "file_a1b2c3d4",
  "entity_id": "entity_123",
  "sector": "finance",
  "confidence": 0.93,
  "events": [
    {
      "event_id": "inv_e5f6g7h8",
      "type": "invoice",
      "invoice_no": "INV21",
      "date": "2025-11-20",
      "vendor": "ABC Supplies",
      "gstin": "27ABCDE1234F2Z5",
      "line_items": [
        {
          "desc": "Item A",
          "qty": 2,
          "unit_price": 100
        }
      ],
      "taxable_total": 200,
      "gst_percent": 18,
      "gst_amount": 36,
      "total": 236,
      "confidence": 0.9,
      "provenance": [
        {
          "file_id": "file_a1b2c3d4",
          "snippet": "INVOICE NO: INV21\nDate: 2025-11-20\nVendor: ABC Supplies...",
          "offset": null
        }
      ]
    }
  ],
  "risks": [
    {
      "risk": "GST mismatch",
      "severity": "high",
      "event_ids": ["inv_e5f6g7h8"],
      "explanation": "GST amount 36 does not match computed 36.0 (expected 18% of 200)"
    }
  ],
  "alerts": [
    {
      "alert_id": "alert_x9y8z7w6",
      "title": "GST mismatch detected",
      "severity": "high",
      "reason": "GST amount 36 does not match computed 36.0 (expected 18% of 200)",
      "source_file": "file_a1b2c3d4",
      "evidence": [
        {
          "file_id": "file_a1b2c3d4",
          "snippet": "GST: 36",
          "page": null
        }
      ],
      "recommended_actions": [
        "Review invoice",
        "Contact vendor"
      ],
      "created_at": "2025-12-07T10:30:00.123456"
    }
  ],
  "core_reasoner": {
    "timeline_updated": true,
    "events_stored": ["inv_e5f6g7h8"],
    "vector_db_updated": true,
    "chunks_stored": 5
  }
}
```

### Example 2: Healthcare Lab Report

**Response:**
```json
{
  "status": "success",
  "file_id": "file_h1e2a3l4",
  "entity_id": "entity_patient_77",
  "sector": "healthcare",
  "confidence": 0.95,
  "events": [
    {
      "event_id": "lab_l1a2b3c4",
      "type": "lab_result",
      "test": "HBA1C",
      "value": 8.1,
      "units": "%",
      "ref_range": "4.0-6.0",
      "date": "2025-11-30",
      "abnormal": true,
      "confidence": 0.94,
      "provenance": [
        {
          "file_id": "file_h1e2a3l4",
          "snippet": "HbA1c: 8.1% (ref 4.0-6.0)",
          "page": 2
        }
      ]
    },
    {
      "event_id": "med_m5e6d7i8",
      "type": "medication",
      "name": "Metformin",
      "dose": "500 mg",
      "frequency": "2x/day",
      "start_date": "2025-10-01",
      "confidence": 0.88,
      "provenance": [...]
    }
  ],
  "risks": [
    {
      "risk": "Abnormal HBA1C value",
      "severity": "high",
      "event_ids": ["lab_l1a2b3c4"],
      "explanation": "HBA1C = 8.1 is outside normal range (4.0-6.0)"
    }
  ],
  "alerts": [
    {
      "alert_id": "alert_h9e0a1l2",
      "title": "High HbA1c detected",
      "severity": "high",
      "reason": "HBA1C = 8.1 is outside normal range (4.0-6.0) - indicates poor glycemic control",
      "source_file": "file_h1e2a3l4",
      "evidence": [
        {
          "file_id": "file_h1e2a3l4",
          "snippet": "HbA1c: 8.1%",
          "page": 2
        }
      ],
      "recommended_actions": [
        "Schedule HbA1c follow-up",
        "Consult endocrinologist"
      ],
      "created_at": "2025-12-07T10:30:00.123456"
    }
  ],
  "core_reasoner": {
    "timeline_updated": true,
    "events_stored": ["lab_l1a2b3c4", "med_m5e6d7i8"],
    "vector_db_updated": true,
    "chunks_stored": 8
  }
}
```

### Example 3: Agriculture Sensor Data

**Response:**
```json
{
  "status": "success",
  "file_id": "file_a9g8r7i6",
  "entity_id": "entity_farm_123",
  "sector": "agriculture",
  "confidence": 0.87,
  "events": [
    {
      "event_id": "soil_s1o2i3l4",
      "type": "soil_moisture",
      "value": 12,
      "units": "%",
      "date": "2025-12-06",
      "field_id": "field_9",
      "confidence": 0.9,
      "provenance": [...]
    },
    {
      "event_id": "ndvi_n5d6v7i8",
      "type": "ndvi",
      "value": 0.45,
      "date": "2025-12-05",
      "field_id": "field_9",
      "confidence": 0.9,
      "provenance": [...]
    }
  ],
  "risks": [
    {
      "risk": "Low soil moisture",
      "severity": "medium",
      "event_ids": ["soil_s1o2i3l4"],
      "explanation": "Soil moisture 12% is below threshold (18%)"
    }
  ],
  "alerts": [
    {
      "alert_id": "alert_a9g8r7i6",
      "title": "Irrigation recommended for Field 9",
      "severity": "medium",
      "reason": "Soil moisture dropped to 12% (threshold 18%)",
      "source_file": "file_a9g8r7i6",
      "evidence": [...],
      "recommended_actions": [
        "Irrigate 20 minutes",
        "Check irrigation system"
      ],
      "created_at": "2025-12-07T10:30:00.123456"
    }
  ],
  "core_reasoner": {
    "timeline_updated": true,
    "events_stored": ["soil_s1o2i3l4", "ndvi_n5d6v7i8"],
    "vector_db_updated": true,
    "chunks_stored": 3
  }
}
```

## POST /upload - Simple Upload Response

**Request:**
```bash
POST /upload
file: document.pdf
```

**Response:**
```json
{
  "status": "success",
  "file_id": "file_a1b2c3d4",
  "raw_file": "storage/files/file_a1b2c3d4.pdf",
  "meta": {
    "filename": "document.pdf",
    "uploaded_at": "2025-12-07T10:30:00.123456",
    "uploader": null,
    "file_size": 245678,
    "file_type": "pdf"
  }
}
```

## GET /timeline/{entity_id} - Timeline Response

**Request:**
```bash
GET /timeline/entity_123?limit=50
```

**Response:**
```json
{
  "status": "success",
  "entity_id": "entity_123",
  "timeline": [
    {
      "event_id": "inv_e5f6g7h8",
      "type": "invoice",
      "invoice_no": "INV21",
      "date": "2025-11-20",
      "vendor": "ABC Supplies",
      "total": 236,
      ...
    },
    {
      "event_id": "lab_l1a2b3c4",
      "type": "lab_result",
      "test": "HBA1C",
      "value": 8.1,
      "date": "2025-11-30",
      ...
    }
  ]
}
```

## POST /chat/{entity_id} - Chatbot Response

**Request:**
```bash
POST /chat/entity_123
Content-Type: application/json
{
  "query": "What are the risks in my documents?"
}
```

**Response:**
```json
{
  "status": "success",
  "entity_id": "entity_123",
  "query": "What are the risks in my documents?",
  "answer": "Based on your documents, I found several risks:\n\n1. **GST Mismatch**: Invoice INV21 has a GST calculation error. The GST amount (36) doesn't match the expected calculation (18% of 200 = 36.0).\n\n2. **High HbA1c**: Your lab report shows HbA1c of 8.1%, which is above the normal range (4.0-6.0%), indicating poor glycemic control.\n\n3. **Low Soil Moisture**: Field 9 has soil moisture at 12%, which is below the recommended threshold of 18%.\n\nI recommend reviewing these issues and taking the suggested actions.",
  "sources": [
    {
      "text": "INVOICE NO: INV21\nDate: 2025-11-20\nGST: 36...",
      "file_id": "file_a1b2c3d4",
      "relevance": 0.95
    },
    {
      "text": "HbA1c: 8.1% (ref 4.0-6.0)...",
      "file_id": "file_h1e2a3l4",
      "relevance": 0.92
    }
  ]
}
```

## Key Response Fields Explained

- **status**: Always "success" for successful operations
- **file_id**: Unique identifier for the uploaded file
- **entity_id**: Identifier for the user/company/patient (auto-generated if not provided)
- **sector**: Detected sector (healthcare, finance, agriculture, etc.)
- **confidence**: How confident the system is about the sector classification (0.0-1.0)
- **events**: Extracted structured data from the document
- **risks**: Detected risks/issues in the document
- **alerts**: Actionable alerts with evidence and recommended actions
- **core_reasoner**: Status of database and vector DB operations

