import threading
from functools import lru_cache

from google import genai
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = False
    gemini_api_key: str = ""

    writer_model: str = "gemini-flash-latest"
    cheap_model: str = "gemma-4-26b-a4b-it"
    image_model: str = "gemini-3.1-flash-image"
    writer_thinking_level: str = "low"
    media_bucket: str = ""


@lru_cache
def settings() -> Settings:
    return Settings()


_clients: dict[str, genai.Client] = {}
_client_lock = threading.Lock()


def genai_client(purpose: str = "text") -> genai.Client:
    """One client per purpose, so a slow image call never shares a pool with text calls.

    Created under a lock: a duplicate created concurrently is garbage-collected
    and closes its HTTP pool under the caller.
    """
    if purpose not in _clients:
        with _client_lock:
            if purpose not in _clients:
                _clients[purpose] = _make_client()
    return _clients[purpose]


def _make_client() -> genai.Client:
    s = settings()
    if s.google_genai_use_vertexai:
        return genai.Client(vertexai=True, project=s.google_cloud_project, location=s.google_cloud_location)
    if not s.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY missing in .env")
    return genai.Client(api_key=s.gemini_api_key)
