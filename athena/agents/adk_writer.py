"""Writer as an ADK agent that must pass the verifier tool (writer_engine="adk").

The agent drafts a story and calls `verify_story`. The tool runs the same code checks
as the loop engine (letters the child can read + story shape). Code ends the turn:
  - the moment the tool accepts a draft, `skip_summarization` stops the agent and that
    exact draft is the result (the model cannot alter it afterwards);
  - after MAX_CHECKS rejected drafts the agent is stopped and generate() falls back.
The final story is re-verified by generate() anyway: the agent never has the last word.
"""

import os
import time
import uuid
from collections.abc import Callable
from functools import lru_cache

from google.genai import types

from athena.agents.writer import build_prompt
from athena.config import settings
from athena.models import StoryDraft, StoryPlan, Usage, ViolationOut

MAX_CHECKS = 3
Check = Callable[[str, list[str]], list[ViolationOut]]

AGENT_RULES = """
How to work:
- Write a draft, then call verify_story(title, sentences, scene) ONCE.
- If it returns ok=true you are done: do not call it again and do not reply.
- If it lists violations, rewrite the draft so none of those words appear, and call it again.
- You have at most 3 calls."""


@lru_cache
def _runtime() -> None:
    """ADK builds its own genai client from the environment: point it at Vertex AI."""
    s = settings()
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE" if s.google_genai_use_vertexai else "FALSE")
    if s.gemini_api_key:
        os.environ.setdefault("GOOGLE_API_KEY", s.gemini_api_key)
    elif s.google_cloud_project:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", s.google_cloud_project)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", s.google_cloud_location)


def write_with_tool(plan: StoryPlan, check: Check) -> tuple[StoryDraft | None, list[dict], Usage, int]:
    """Returns (accepted draft or None, every tool check made, token usage, latency ms)."""
    _runtime()
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import ToolContext

    checks: list[dict] = []
    accepted: list[StoryDraft] = []

    def verify_story(title: str, sentences: list[str], scene: str, tool_context: ToolContext) -> dict:
        """Check a draft story for this child. Returns ok, or every word the child cannot read
        yet (with the letter that blocks it) and every word or sentence that is too long."""
        violations = check(title, sentences)
        checks.append({"title": title, "sentences": sentences, "violations": violations})
        if not violations:
            accepted.append(StoryDraft(title=title, sentences=sentences, scene=scene))
            tool_context.actions.skip_summarization = True  # code ends the turn on acceptance
        elif len(checks) >= MAX_CHECKS:
            tool_context.actions.skip_summarization = True  # out of checks: generate() falls back
        return {
            "ok": not violations,
            "violations": [{"word": v.word, "letter": v.unit, "reason": v.reason} for v in violations[:12]],
        }

    agent = LlmAgent(
        name="writer",
        description="Writes a decodable story for one child; must pass the verifier tool.",
        model=settings().writer_model,
        instruction=build_prompt(plan) + AGENT_RULES,
        tools=[verify_story],
        generate_content_config=types.GenerateContentConfig(
            temperature=0.9,
            max_output_tokens=4096,
            thinking_config=types.ThinkingConfig(thinking_level=settings().writer_thinking_level),
        ),
    )
    runner = Runner(agent=agent, app_name="athena", session_service=InMemorySessionService(), auto_create_session=True)
    usage = Usage(model=settings().writer_model)
    t0 = time.perf_counter()
    msg = types.Content(role="user", parts=[types.Part(text="Write the story now.")])
    for ev in runner.run(user_id="athena", session_id=uuid.uuid4().hex, new_message=msg):
        um = getattr(ev, "usage_metadata", None)
        if um:
            usage.input_tokens += um.prompt_token_count or 0
            usage.output_tokens += um.candidates_token_count or 0
            usage.thinking_tokens += um.thoughts_token_count or 0
        if accepted or len(checks) >= MAX_CHECKS:
            break
    return (accepted[0] if accepted else None), checks, usage, int((time.perf_counter() - t0) * 1000)
