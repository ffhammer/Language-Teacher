from pydantic import BaseModel, Field

from src.config import INITIAL_PROMPT, LEVEL, SOURCE_LANGUAGE, TARGET_LANGUAGE
from src.llm import gemini_structured_ouput

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

    @classmethod
    def generate(
        cls, title: str, generation_instruction: str, purpose: str, timeout: float = 10
    ):
        system_prompt = (
            f"{INITIAL_PROMPT}\n\n"
            "You are generating a sentence order (reordering) language learning task for a student learning "
            f"{TARGET_LANGUAGE} (instruction language: {SOURCE_LANGUAGE}, level: {LEVEL}).\n"
            "Task type: sentence_order.\n"
            f"Description: The learner is given a sentence in {SOURCE_LANGUAGE} and words in {TARGET_LANGUAGE} along with some distraction words. "
            "The user must reorder the words to form a correct sentence.\n"
            "When to use: Ideal for translation, sentence structure, word order, and understanding how sentences are formed in the target language.\n"
            "You will receive a title, a generation instruction, and a purpose for the task, along with a JSON output schema. "
            "Focus on generating high-quality, level-appropriate content based on the provided details. "
            "Ensure the output strictly follows the given schema."
        )
        contents = f"Title: {title}\n\nGeneration Instruction: {generation_instruction}\n\nPurpose: {purpose}"
        # Generate a SentenceOrderTask instance using the LLM
        sentence_order_task = gemini_structured_ouput(
            system_prompt=system_prompt, contents=contents, Schema=cls, timeout=timeout
        )
        if sentence_order_task is None:
            return None
        # Convert to DraggingTask for actual use
        return sentence_order_task.to_task()
