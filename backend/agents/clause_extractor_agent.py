"""Clause extraction with semantic harmful‑clause detection.

Uses a semantic rule engine (works offline, understands clause structure)
with optional LLM enhancement for edge cases.
"""
import asyncio
import re
from typing import Dict, List, Optional, Tuple

from backend.agents.classifier import classify_clause


async def extract_clauses_from_file(content: bytes) -> List[Dict]:
    """Extract clauses from the given file bytes and classify each as harmful or not.

    Classification uses:
    1. Semantic rule engine (primary — understands clause structure, direction of
       obligations, dollar amounts, time periods — works offline)
    2. LLM enhancement (optional — when configured, catches edge cases)
    """
    text = content.decode(errors="ignore")
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
        if "." in first:
            heading_part, remainder = first.split(".", 1)
            header = heading_part.strip() + "."
            body = remainder.strip()
        else:
            header = first.rstrip(":")
            body = ""
        if len(lines) > 1:
            body = (("\n".join([body] + lines[1:])).strip() if body else "\n".join(lines[1:]).strip())
        harmful, reason = await asyncio.to_thread(classify_clause, header, body)
        extracted.append({
            "name": header,
            "content": body,
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
