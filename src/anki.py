from sqlmodel import SQLModel, Field, Column, LargeBinary, Enum
from typing import Optional
from datetime import date, timedelta
from enum import StrEnum


class CardCategory(StrEnum):
    regular_verb = "verb"
    irregular_verb = "irregular_verb"
    noun = "noun"
    adjective = "adjective"
    adverb = "adverb"
    phrase = "phrase"
    idiom = "idiom"
    expression = "expression"
    grammar = "grammar"
    sentence = "sentence"
    question = "question"
    number = "number"
    preposition = "preposition"
    conjunction = "conjunction"
    pronoun = "pronoun"
    article = "article"
    proverb = "proverb"
    slang = "slang"
    cultural_note = "cultural note"


class AnkiCard(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(None, primary_key=True, index=True)

    easiness_factor: float = Field(
        default=2.5,
        description="Easiness factor for the card (SM2 algorithm)",
        index=True,
    )
    repetitions: int = Field(
        default=0, description="Number of times the card has been reviewed"
    )
    interval: int = Field(default=0, description="Interval in days until next review")
    quality: int = Field(default=0, description="Last review quality rating (0-5)")

    a_content: str = Field(description="The Content of one site")
    b_content: str = Field(description="The Content of translation/other site")
    notes: Optional[str] = Field(
        None, description="Optional notes and context or examples"
    )

    next_date: date = Field(default_factory=date.today, index=True)
    a_mp3: Optional[bytes] = Field(
        default=None, sa_column=Column(LargeBinary), description="Audio for a_content"
    )
    b_mp3: Optional[bytes] = Field(
        default=None, sa_column=Column(LargeBinary), description="Audio for b_content"
    )
    category: CardCategory = Field(
        sa_column=Column(Enum(CardCategory), index=True, nullable=False)
    )


def update_card(card: AnkiCard, quality: int) -> None:
    assert 0 <= quality <= 5
    # SM2 core
    if quality == 0:
        card.repetitions = 0
        card.interval = 0
    elif quality < 3:
        card.repetitions = 0
        card.interval = 1
    else:
        card.repetitions += 1
        if card.repetitions == 1:
            card.interval = 1
        elif card.repetitions == 2:
            card.interval = 6
        else:
            card.interval = int(card.interval * card.easiness_factor)
    # update EF
    card.easiness_factor = max(
        1.3,
        card.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    card.quality = quality
    card.next_date = date.today() + timedelta(days=card.interval)
