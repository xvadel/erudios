from __future__ import annotations

from pydantic import BaseModel


class SectionInfo(BaseModel):
    slug: str
    title: str


class ShellOut(BaseModel):
    topic_slug: str
    overview: str
    sections: list[SectionInfo]


class SectionOut(BaseModel):
    topic_slug: str
    section_slug: str
    content: str
    has_overlay: bool
    degraded: bool


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str


class QuizOut(BaseModel):
    topic_slug: str
    section_slug: str
    questions: list[QuizQuestion]
