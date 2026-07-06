"""Contract clause classifier.

Three-layer approach:
1. Semantic rule engine (primary — works offline, no dependencies)
2. LLM enhancement (optional — OpenAI or HuggingFace)
3. Regex fallback (last resort for uncovered categories)
"""
import json
import logging
from typing import Optional, Tuple

import requests

from backend.core.config import settings
from backend.agents.rule_engine import analyze_clause

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are a legal contract analyst. Analyze the following clause and determine if it is HARMFUL or UNHARMFUL to the client (the receiving party).

A clause is HARMFUL if it is unreasonably one-sided against the client:
- Unilateral termination rights for the provider only
- Extremely low liability caps ($1, $50, etc.) with no carve-outs for gross negligence, IP infringement, or confidentiality breaches
- Requiring the client to indemnify the provider for the provider's own negligence or security flaws
- Automatic renewal with unreasonable cancellation windows or massive automatic price increases
- Perpetual, irrevocable, royalty-free licenses to client data, feedback, or materials
- Retroactive pricing adjustments or hidden fees charged without notice
- Deemed acceptance clauses with unreasonably short review periods
- Waiving all warranties or remedies entirely
- Provider ownership of all derivative works or custom features even when client funded them
- Payment obligations surviving termination for 10+ years

Clause heading: {heading}
Clause text: {text}

Respond with valid JSON only, no markdown, no code fences, no extra text:
{{"harmful": true, "reason": "concise explanation"}}
or
{{"harmful": false, "reason": "concise explanation"}}"""


def classify_clause(heading: str, text: str) -> Tuple[bool, str]:
    """Classify a clause as harmful or unharmful.

    Returns (is_harmful: bool, reason: str).

    Uses the semantic rule engine as the primary classifier (works offline,
    understands clause structure).  If configured, enhances with LLM to catch
    edge cases the rules might miss.
    """
    if not text.strip():
        return False, ""

    # 1. Semantic rule engine (primary)
    rule_harmful, rule_reason = analyze_clause(heading, text)

    # 2. Optional LLM enhancement
    llm_result = _classify_with_llm(heading, text)

    if llm_result is not None:
        llm_harmful, llm_reason = llm_result
        # If either flags it as harmful, report it
        if llm_harmful:
            if rule_harmful:
                return True, f"{rule_reason}; LLM: {llm_reason}"
            return True, llm_reason
        if rule_harmful:
            return True, rule_reason
        return False, ""

    # LLM unavailable — rely on rule engine
    if rule_harmful:
        return True, rule_reason
    return False, ""


# ── LLM helper ──────────────────────────────────────────────────────

_llm_unavailable: bool = False


def _classify_with_llm(heading: str, text: str) -> Optional[Tuple[bool, str]]:
    global _llm_unavailable
    if _llm_unavailable:
        return None

    prompt = CLASSIFICATION_PROMPT.format(heading=heading, text=text)
    provider = settings.LLM_PROVIDER.lower()

    try:
        if provider == "openai":
            return _classify_openai(prompt)
        return _classify_huggingface(prompt)
    except Exception as e:
        logger.debug("LLM classifier unavailable: %s", e)
        _llm_unavailable = True
        return None


def _parse_response(raw: str) -> Optional[Tuple[bool, str]]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        return bool(data.get("harmful", False)), str(data.get("reason", ""))
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.debug("Failed to parse LLM response: %s", e)
        return None


def _classify_openai(prompt: str) -> Optional[Tuple[bool, str]]:
    try:
        from openai import OpenAI
    except ImportError:
        return None
    api_key = settings.LLM_API_KEY
    if not api_key:
        return None
    client = OpenAI(api_key=api_key, base_url=settings.LLM_ENDPOINT or None)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL or "gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=300,
        timeout=15,
    )
    raw = response.choices[0].message.content or ""
    return _parse_response(raw)


def _classify_huggingface(prompt: str) -> Optional[Tuple[bool, str]]:
    headers = {"Content-Type": "application/json"}
    api_key = settings.HF_API_KEY
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.1,
            "return_full_text": False,
        },
    }
    response = requests.post(
        settings.LLM_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        raw = data[0].get("generated_text", "")
    elif isinstance(data, dict):
        raw = data.get("generated_text", "")
    else:
        raw = str(data)
    return _parse_response(raw)
