import threading
from pathlib import Path
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic_settings import BaseSettings, SettingsConfigDict


# Repo-root .env, regardless of the directory the server is started from.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = False
    gemini_api_key: str = ""

    writer_model: str = "gemini-3.8-flash"
    cheap_model: str = "gemma-4-26b-a4b-it"
    safety_model: str = "gemini-3.1-flash-lite"  # fast screen; Gemma is not a plain API on Vertex
    image_model: str = "gemini-3.1-flash-image"
    writer_thinking_level: str = "low"
    writer_engine: str = "loop"  # "loop": code feedback loop · "adk": ADK agent with verifier tool
    media_bucket: str = ""
    store_backend: str = "file"  # "file" (local dev) | "firestore" (Cloud Run: survives restarts)
    firestore_prefix: str = ""  # collection prefix, e.g. "dev_" to keep tests apart
    state_dir: str = str(Path(__file__).resolve().parent.parent / "state")  # learners.json
    google_oauth_client_id: str = ""  # "Sign in with Google" (a Web OAuth client id; public, not a secret)
    request_timeout_ms: int = 30_000  # normal calls 2-15s; cut runaway thinking and retry


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
    # Without a timeout a stalled request hangs forever (seen in eval).
    http = types.HttpOptions(timeout=s.request_timeout_ms)
    if s.google_genai_use_vertexai:
        if s.gemini_api_key:  # Vertex AI API key (AQ.…): billed to the key's project
            return genai.Client(vertexai=True, api_key=s.gemini_api_key, http_options=http)
        return genai.Client(
            vertexai=True, project=s.google_cloud_project, location=s.google_cloud_location, http_options=http
        )
    if not s.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY missing in .env")
    return genai.Client(api_key=s.gemini_api_key, http_options=http)
