from pydantic import BaseModel, Field

from .dragging_task import DragAndDropTaskRow, DraggingTask


class SentenceOrderTask(BaseModel):
    title: str = Field(description="Short, descriptive title for the translation task")
    subtitle: str = Field(
        description="Instructions or context for the translation activity"
    )
    source_sentence: str = Field(
        description="First sentence in the source language (Language A)"
    )
    target_sentence: str = Field(
        description="Correct translation of the sentences in the target language"
    )
    distractor_words: list[str] = Field(
        description="Extra words to increase task difficulty"
    )

    def to_task(self) -> DraggingTask:
        sentence = "".join([f"${word}$" for word in self.source_sentence.split()]) + " "

        return DraggingTask(
            title=self.title,
            suptitle=f"{self.subtitle}\n\nSentence:{self.source_sentence}",
            rows=[
                DragAndDropTaskRow(
                    sentence=sentence, distractions=self.distractor_words
                )
            ],
        )
