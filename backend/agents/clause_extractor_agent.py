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


_SECTION_RE = re.compile(
    r"(?:SECTION|Section|ARTICLE|Article|CLAUSE|Clause)\s+\d+\s*[:.]?\s*"
)

def _parse_clauses(text: str) -> List[Dict]:
    blocks = re.split(r"(?:\r?\n){2,}", text)
    if len(blocks) <= 2 and len(text) > 300:
        blocks = _SECTION_RE.split(text)
        if len(blocks) > 2:
            labels = _SECTION_RE.findall(text)
            partitioned = []
            for idx, block in enumerate(blocks):
                block = block.strip()
                if not block:
                    continue
                label = (labels[idx - 1] if idx > 0 else "") if labels else ""
                partitioned.append({"header": label, "body": block})
            blocks = partitioned
            if blocks and blocks[0]["header"] == "":
                blocks = blocks[1:]
            return [
                {"header": b["header"], "body": b["body"]}
                for b in blocks
            ]

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
