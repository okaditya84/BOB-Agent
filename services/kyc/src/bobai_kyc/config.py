"""KYC service configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

def _default_kb_path() -> str:
    """Find the BoB KB by searching upward; robust to both local and container layouts.

    In containers the path is supplied via BOBAI_KYC_KB_PATH (this is only the default).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "bob_documents_data.json"
        if candidate.exists():
            return str(candidate)
    return "data/bob_documents_data.json"


_DEFAULT_KB = _default_kb_path()


def _default_model(filename: str) -> str:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "models" / filename
        if candidate.exists():
            return str(candidate)
    return f"data/models/{filename}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOBAI_KYC_", env_file=".env", extra="ignore")

    # Path to the BoB document knowledge base (JSON).
    kb_path: str = str(_DEFAULT_KB)

    # Face-match model paths (YuNet detector + SFace recognizer, OpenCV Zoo).
    yunet_path: str = _default_model("face_detection_yunet_2023mar.onnx")
    sface_path: str = _default_model("face_recognition_sface_2021dec.onnx")

    # Vision LLM (Groq) for document-type classification. Key read from GROQ_API_KEY.
    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_base_url: str = "https://api.groq.com/openai/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
