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


# Split patterns tried in order for PDF-extracted text
_SPLIT_PATTERNS = [
    re.compile(r"(?:SECTION|Section|ARTICLE|Article|CLAUSE|Clause)\s+\d+\s*[:.]?\s*"),
    re.compile(r"\b(?:SECTION|Section|ARTICLE|Article|CLAUSE|Clause)\s+\d+\s*[:.]?\s*"),
    re.compile(r"(?:^|\s)\[HARMFUL\]\s*|\s*\[UNHARMFUL\]\s*"),
    re.compile(r"\n\s*\d+\.\s+(?=[A-Z])"),
]

def _split_sections(text: str) -> List[Dict]:
    for pat in _SPLIT_PATTERNS:
        blocks = pat.split(text)
        blocks = [b.strip() for b in blocks if b.strip()]
        if len(blocks) > 2:
            labels = pat.findall(text)
            result = []
            for idx, block in enumerate(blocks):
                label = labels[idx - 1].strip() if idx > 0 and labels else ""
                if not label:
                    label = ""
                clean = pat.sub("", block) if label else block
                result.append({"header": label, "body": clean})

            if result and not result[0]["header"]:
                result = result[1:]

            combined = []
            cur = None
            for r in result:
                if r["header"]:
                    if cur:
                        combined.append(cur)
                    cur = r
                elif cur:
                    cur["body"] += " " + r["body"]
                else:
                    cur = r
            if cur:
                combined.append(cur)

            if len(combined) >= 3:
                return combined
    return []


def _parse_clauses(text: str) -> List[Dict]:
    blocks = re.split(r"(?:\r?\n){2,}", text)
    if len(blocks) <= 2 and len(text) > 100:
        sections = _split_sections(text)
        if sections:
            return sections

    extracted = []
    for block in blocks:
        block = block.strip() if isinstance(block, str) else block
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
        extracted.append({"header": header, "body": body})
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
