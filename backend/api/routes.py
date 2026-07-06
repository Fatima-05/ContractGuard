# backend/api/routes.py
"""API route definitions for ContractGuard.
Provides endpoint to extract clauses from uploaded documents.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

# Import the clause extraction agent function (assume it exists)
try:
    from backend.agents.clause_extractor_agent import extract_clauses_from_file
except ImportError as e:
    raise ImportError("Clause extractor agent not found: " + str(e))

router = APIRouter()

@router.post("/extract")
async def extract_clauses(file: UploadFile = File(...)):
    """Accept a document file and return extracted clauses.
    The file is passed to the clause extraction pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    content = await file.read()
    try:
        clauses = await extract_clauses_from_file(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    # Overall risk is true if any clause is flagged as harmful
    overall_risk = any(c.get("harmful") for c in clauses)
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + "Z"
    return {"clauses": clauses, "overall_risk": overall_risk, "timestamp": timestamp}

@router.get("/ping")
async def ping():
    return {"status": "ok"}
