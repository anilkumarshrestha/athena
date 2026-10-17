"""Illustrator: one flat picture-book image per story.

Starts from the planner's theme, in parallel with the writer, so the image never
waits on the verified text.
"""

import time
import zlib

from google.genai import types

from athena.config import genai_client, settings
from athena.models import Usage
from athena.retry import with_retry

# DESIGN.md §8. Keeps illustrations inside the UI palette.
STYLE = (
    "Bright, cheerful flat vector children's book illustration, in the spirit of Cocomelon or "
    "Duolingo ABC. Light sky-blue background #EAF6FF. Vivid saturated palette: sky blue #38A8FF, "
    "grass green #3DBB4F, sunny yellow #FFC800, coral red #FF5A5F, deep navy #1E2A4A for thick "
    "rounded outlines. Big simple rounded shapes, no gradients, no text, no letters. Animals or "
    "objects as main characters; any people shown small, simple, no detailed faces. Not "
    "photorealistic. Setting: rural or small-town Nepal."
)

# One dominant accent per story, picked from the theme so a retry keeps its colour.
ACCENTS = ("sunny yellow", "coral red", "grass green", "sky blue")


def build_prompt(theme: str) -> str:
    accent = ACCENTS[zlib.crc32(theme.encode()) % len(ACCENTS)]
    return f"Picture for a story about: {theme}.\n\nMain character in {accent}.\n\n{STYLE}"


def illustrate(theme: str) -> tuple[bytes, str, Usage, int]:
    """Returns (image bytes, mime type, usage, latency ms)."""
    s = settings()
    t0 = time.perf_counter()
    r = with_retry(
        lambda: genai_client("image").models.generate_content(
            model=s.image_model,
            contents=build_prompt(theme),
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="4:3"),
            ),
        ),
        "illustrator",
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    for part in r.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            um = r.usage_metadata
            usage = Usage(
                model=r.model_version or s.image_model,
                input_tokens=um.prompt_token_count or 0,
                output_tokens=um.candidates_token_count or 0,
            )
            return part.inline_data.data, part.inline_data.mime_type or "image/png", usage, latency_ms
    raise RuntimeError("illustrator returned no image")
