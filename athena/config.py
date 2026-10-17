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


@lru_cache
def settings() -> Settings:
    return Settings()


@lru_cache
def genai_client() -> genai.Client:
    s = settings()
    if s.google_genai_use_vertexai:
        return genai.Client(vertexai=True, project=s.google_cloud_project, location=s.google_cloud_location)
    if not s.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY missing in .env")
    return genai.Client(api_key=s.gemini_api_key)
