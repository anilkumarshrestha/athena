"""Illustrator: one flat picture-book image per story.

Starts from the planner's theme, in parallel with the writer, so the image never
waits on the verified text.
"""

import time

from google.genai import types

from athena.config import genai_client, settings
from athena.models import Usage

# DESIGN.md §8, verbatim. Keeps illustrations inside the UI palette.
STYLE = (
    "Simple flat vector children's book illustration. Warm off-white background #FBF7F0. "
    "Limited palette: deep blue #1E4FB5, leaf green #1F7A3E, ochre #9A5B00, terracotta #B3360B, "
    "teal #0B6E7A, warm dark brown #1F1B16 for outlines. Soft rounded shapes, no gradients, no text, "
    "no letters. Animals or objects as main characters; any people shown small, simple, no detailed "
    "faces. Not photorealistic. Setting: rural or small-town Nepal."
)


def build_prompt(theme: str) -> str:
    return f"Picture for a story about: {theme}.\n\n{STYLE}"


def illustrate(theme: str) -> tuple[bytes, str, Usage, int]:
    """Returns (image bytes, mime type, usage, latency ms)."""
    s = settings()
    t0 = time.perf_counter()
    r = genai_client("image").models.generate_content(
        model=s.image_model,
        contents=build_prompt(theme),
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="4:3"),
        ),
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
