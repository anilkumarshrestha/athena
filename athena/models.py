"""Pydantic models at the API / model-output boundary. The verifier core stays stdlib."""

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["ne", "en"]
Outcome = Literal["first_pass", "regenerated", "pruned", "template", "wordlist"]


class StoryDraft(BaseModel):
    """Writer's structured output."""

    title: str = Field(description="Short title, 1-4 words, same language as the story.")
    sentences: list[str] = Field(description="3-5 short sentences, one per item.")
    scene: str = Field(description="One English sentence describing the picture for the illustrator.")


class ViolationOut(BaseModel):
    word: str
    word_index: int
    unit: str | None
    reason: str


class Usage(BaseModel):
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0


class Attempt(BaseModel):
    n: int
    prompt: str
    title: str
    sentences: list[str]
    violations: list[ViolationOut]
    latency_ms: int
    usage: Usage


class StoryPlan(BaseModel):
    language: Language
    learner_name: str
    theme: str
    key_words: list[str] = []  # readable words for the theme's key things
    avoid_words: list[str] = []  # natural words for them the child cannot read yet
    target_units: list[str]
    word_bank: list[str]
    mastery: list[str]


class GenerationResult(BaseModel):
    plan: StoryPlan
    attempts: list[Attempt]
    outcome: Outcome
    title: str
    sentences: list[str]
    scene: str
    units_used: list[str]
    first_pass_violations: int
    final_violation_count: int
    total_latency_ms: int
