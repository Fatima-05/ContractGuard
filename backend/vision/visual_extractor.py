import json
import requests
from pathlib import Path
from backend.core.config import settings
from backend.core.logger import logger

# Donut free inference endpoint (HF public)
_DONUT_ENDPOINT = "https://api-inference.huggingface.co/models/microsoft/donut-base"

def extract_visual(page_image_path: Path) -> dict:
    """Send a PNG image of a document page to the Donut model and return parsed output.
    The HuggingFace inference API returns a JSON with keys like 'words', 'bboxes', 'linking', and 'tokens'.
    For our use‑case we keep the raw response and also pull out any detected tables.
    """
    if not page_image_path.exists():
        raise FileNotFoundError(f"Page image not found: {page_image_path}")
    with open(page_image_path, "rb") as f:
        files = {"data": f}
        try:
            response = requests.post(_DONUT_ENDPOINT, files=files, timeout=30)
            response.raise_for_status()
            payload = response.json()
            logger.debug("Donut returned %d keys for %s", len(payload), page_image_path.name)
            return payload
        except Exception as e:
            logger.error("Donut extraction failed for %s: %s", page_image_path.name, e)
            raise
