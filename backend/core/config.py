import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # FastAPI
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    # Vector store
    DOC_ROOT: Path = BASE_DIR / "data" / "docs"
    CHUNK_ROOT: Path = BASE_DIR / "data" / "chunks"
    FAISS_INDEX_PATH: Path = BASE_DIR / "data" / "faiss_index.faiss"

    # Visual data (new)
    VISUAL_ROOT: Path = BASE_DIR / "data" / "visual"

    # Model endpoints
    DOC_MODEL_ENDPOINT: str = os.getenv(
        "DOC_MODEL_ENDPOINT",
        "https://api-inference.huggingface.co/models/microsoft/dit-base"
    )

    # LLM classifier settings
    # Provider: "openai" or "huggingface" (default: huggingface — free, no key needed)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "huggingface")
    # Model name (for OpenAI — e.g. gpt-4o-mini, gpt-4o; for HF this is part of the endpoint)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    # API key (required for OpenAI, optional for HF)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    # HuggingFace API key (optional — free tier works without it)
    HF_API_KEY: str = os.getenv("HF_API_KEY", "")
    # LLM endpoint (HF default is Llama 3.1 8B Instruct via free inference API)
    LLM_ENDPOINT: str = os.getenv(
        "LLM_ENDPOINT",
        "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3.1-8B-Instruct"
    )

settings = Settings()
