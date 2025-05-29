from abc import ABC, abstractmethod
from typing import Optional

from sqlmodel import Field, SQLModel

from src.utils import drop_fields_from_schema


class BaseTask(SQLModel, ABC):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(None, primary_key=True, index=True)
    finished: bool = Field(False, index=True)
    excercise_plan_id: int = Field(0, index=True)

    title: str = Field(description="Main title for the task.")
    suptitle: str | None = Field(
        None,
        description="Optional text shown below the title for context.",
    )
    result_description: Optional[str] = Field(
        None, description="An description of the result of a task"
    )
    text_below_task: str | None = Field(
        None,
        description="Optional text or instructions shown after the main task content and feedback.",
    )

    @classmethod
    def model_json_schema(
        cls,
    ):
        schema = super().model_json_schema()
        return drop_fields_from_schema(
            json_schema=schema, fields_to_ignore=["excercise_plan_id", "id", "finished"]
        )

    @abstractmethod
    def display():
        pass

    @abstractmethod
    @classmethod
    def generate(
        cls, title: str, generation_instruction: str, purpose: str, timeout: float = 10
    ) -> Optional["BaseTask"]:
        pass
