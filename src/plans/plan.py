from datetime import date
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import desc
from sqlmodel import Field, Session, SQLModel, select

from src.db import engine
from src.tasks import DraggingTask, FillInTask
from src.tasks.vocab_tasks import VocabTask


class ExercisePlanStatus(BaseModel):
    total_tasks: int
    finished_tasks: int

    @property
    def finished(self) -> bool:
        return self.total_tasks == self.finished_tasks

    def __repr__(self):
        if self.finished:
            return "All tasks finished!"
        else:
            remaining = self.total_tasks - self.finished_tasks
            return f"{remaining} task(s) of {self.total_tasks} total still open"


class ExercisePlan(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(None, primary_key=True, index=True)
    created_at: date = Field(index=True)
    title: str
    goal: str

    @property
    def fill_in_tasks(self) -> list[FillInTask]:
        with Session(engine) as sess:
            return sess.exec(
                select(FillInTask).where(FillInTask.excercise_plan_id == self.id)
            ).all()

    @property
    def dragging_tasks(self) -> list[DraggingTask]:
        with Session(engine) as sess:
            return sess.exec(
                select(DraggingTask).where(DraggingTask.excercise_plan_id == self.id)
            ).all()

    @property
    def vocab_tasks(self) -> list[VocabTask]:
        with Session(engine) as sess:
            return sess.exec(
                select(VocabTask).where(VocabTask.excercise_plan_id == self.id)
            ).all()

    @property
    def status(self):
        fill_in_tasks = self.fill_in_tasks
        fill_in_finished = sum(
            1 for i in fill_in_tasks if getattr(i, "finished", False)
        )

        dragging_tasks = self.dragging_tasks
        dragging_finished = sum(
            1 for i in dragging_tasks if getattr(i, "finished", False)
        )

        vocab_tasks = self.vocab_tasks
        vocab_finished = sum(1 for i in vocab_tasks if getattr(i, "finished", False))

        return ExercisePlanStatus(
            total_tasks=len(dragging_tasks) + len(fill_in_tasks) + len(vocab_tasks),
            finished_tasks=dragging_finished + fill_in_finished + vocab_finished,
        )


def get_last_n_plans(n_plans: int) -> list[ExercisePlan]:
    with Session(engine) as sess:
        return sess.exec(
            select(ExercisePlan).order_by(desc(ExercisePlan.created_at)).limit(n_plans)
        ).all()
