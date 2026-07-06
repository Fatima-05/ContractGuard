import json
import os
from pathlib import Path
from typing import List, Dict, Any

from unstructured.partition.auto import partition
from backend.core.config import settings
from backend.core.logger import logger
from backend.utils.image_utils import pdf_to_images
from backend.vision.visual_extractor import extract_visual

def _save_chunk(chunk: Dict[str, Any]) -> None:
    """Save a text chunk (with metadata) to the chunks directory as JSON."""
    settings.CHUNK_ROOT.mkdir(parents=True, exist_ok=True)
    existing = list(settings.CHUNK_ROOT.glob("chunk_*.json"))
    idx = len(existing) + 1
    path = settings.CHUNK_ROOT / f"chunk_{idx:05d}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunk, f, ensure_ascii=False, indent=2)

def _save_visual(doc_name: str, page_idx: int, visual_json: dict) -> None:
    """Persist Donut visual extraction JSON for a given page.
    Stored under ``settings.VISUAL_ROOT / <doc_name>_page_<idx>.json``.
    """
    settings.VISUAL_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{Path(doc_name).stem}_page_{page_idx:03d}.json"
    path = settings.VISUAL_ROOT / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(visual_json, f, ensure_ascii=False, indent=2)

def ingest_file(file_path: Path) -> List[Dict[str, Any]]:
    """Ingest a contract file.
    Steps:
    1️⃣ Partition with ``unstructured`` to get raw text elements.
    2️⃣ Chunk the text (paragraph split – keep simple for now).
    3️⃣ For PDFs, render each page to PNG and run Donut visual extraction.
    4️⃣ Store text chunks (JSON) and visual JSON per page.
    5️⃣ Return a list of chunk dicts (including embeddings placeholder).
    """
    logger.info("Ingesting %s", file_path.name)
    elements = partition(file_path)

    # -------- Text chunking --------
    chunks: List[Dict[str, Any]] = []
    for elem in elements:
        txt = elem.text.strip()
        if not txt:
            continue
        chunk = {
            "text": txt,
            "metadata": {
                "source_file": str(file_path.name),
                "element_type": elem.__class__.__name__,
                "chunk_strategy": "paragraph",
            },
        }
        _save_chunk(chunk)
        chunks.append(chunk)

    # -------- Visual extraction (PDF only) --------
    if file_path.suffix.lower() == ".pdf":
        logger.info("Running visual extraction on PDF pages")
        # Convert each page to PNG in a temporary folder under VISUAL_ROOT
        pages_dir = settings.VISUAL_ROOT / f"{Path(file_path).stem}_pages"
        image_paths = pdf_to_images(file_path, pages_dir)
        for idx, img_path in enumerate(image_paths, start=1):
            try:
                visual_json = extract_visual(img_path)
                _save_visual(file_path.name, idx, visual_json)
                # Optionally, you could attach a reference to the visual data in a chunk,
                # but we keep them separate for clarity.
            except Exception as exc:
                logger.error("Visual extraction failed for page %d of %s: %s", idx, file_path.name, exc)

    logger.info("Created %d text chunks from %s", len(chunks), file_path.name)
    return chunks
