"""Clause extraction with semantic harmful-clause detection.

Uses a semantic rule engine (works offline, understands clause structure)
with optional LLM enhancement for edge cases.
"""
import asyncio
import io
import re
from typing import Dict, List

from backend.agents.classifier import classify_clause


def _extract_text(content: bytes) -> str:
    if content[:5] == b"%PDF-":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
            return "\n\n".join(pages)
        except Exception:
            return content.decode(errors="ignore")
    return content.decode(errors="ignore")


def _parse_clauses(text: str) -> List[Dict]:
    blocks = re.split(r"(?:\r?\n){2,}", text)
    extracted = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        while lines and (lines[0].startswith("[ID:") or lines[0].startswith("---")):
            lines.pop(0)
        if not lines:
            continue
        first = lines[0]
        if "." in first and first.index(".") < 5:
            header = first.split(".", 1)[0].strip() + "."
            body = first.split(".", 1)[1].strip()
        else:
            header = first.rstrip(":")
            body = ""
        if len(lines) > 1:
            body = (("\n".join([body] + lines[1:])).strip() if body else "\n".join(lines[1:]).strip())
        extracted.append({"header": header, "body": body, "lines": lines})
    return extracted


async def extract_clauses_from_file(content: bytes) -> List[Dict]:
    """Extract clauses from the given file bytes and classify each."""
    text = _extract_text(content)
    clauses = _parse_clauses(text)
    extracted = []
    for c in clauses:
        harmful, reason = await asyncio.to_thread(classify_clause, c["header"], c["body"])
        extracted.append({
            "name": c["header"],
            "content": c["body"],
            "harmful": harmful,
            "reason": [reason] if reason else [],
        })
    if not extracted:
        extracted.append({
            "name": "Unknown",
            "content": text,
            "harmful": False,
            "reason": [],
        })
    return extracted
