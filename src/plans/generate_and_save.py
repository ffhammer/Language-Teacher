from datetime import date

import streamlit as st
from loguru import logger
from sqlmodel import Session
from streamlit import runtime
from tqdm import tqdm

from src.db import engine
from src.llm import retry_n_times
from src.tasks import (
    BaseTask,
    DraggingTask,
    FillInTask,
    SentenceOrderTask,
    VocabTask,
)

from .plan import ExercisePlan
from .planning import StudyPlan, TaskCategories

category_to_task = {
    TaskCategories.DRAG_AND_DROP: DraggingTask,
    TaskCategories.FILL_IN: FillInTask,
    TaskCategories.SENTENCE_ORDER: SentenceOrderTask,
    TaskCategories.VOCAB: VocabTask,
}


def generate_and_save(plan: StudyPlan, n_retries=3, timeout=10):
    db_plan = ExercisePlan(title=plan.title, goal=plan.goal, created_at=date.today())

    generated_tasks_instances: list[BaseTask] = []
    for i, task_definition in enumerate(
        tqdm(plan.tasks, desc="Generating task content")
    ):
        cls: type[BaseTask] = category_to_task[task_definition.category]

        task_generation_func = retry_n_times(n=n_retries)(
            cls.generate,
        )

        generated_task_instance: BaseTask | None = task_generation_func(
            title=task_definition.title,
            generation_instruction=task_definition.generation_instruction,
            purpose=task_definition.purpose,
            timeout=timeout,
        )

        if generated_task_instance is None:
            logger.error(
                f"Failed to generate task content for: {task_definition.title} after {n_retries} retries."
            )
            # Optionally, raise an error or decide how to handle partial plan generation
            raise RuntimeError(
                f"Could not generate task: {task_definition.title}"
            )  # Or continue if partial plans are acceptable

        if runtime.exists():
            st.progress((i + 1) / len(plan.tasks))

        generated_task_instance.position = i
        generated_tasks_instances.append(generated_task_instance)

    with Session(engine, expire_on_commit=False) as sess:
        sess.add(db_plan)
        sess.flush()
        sess.commit()
        assert db_plan.id is not None
        for task_instance in tqdm(
            generated_tasks_instances, desc="Saving tasks to database"
        ):
            task_instance.excercise_plan_id = db_plan.id  # Correctly assign the plan ID
            sess.add(task_instance)

        # Single commit for all tasks and their related objects (e.g., AnkiCards)
        sess.commit()
    logger.info(
        f"Successfully generated and saved plan '{db_plan.title}' with {len(generated_tasks_instances)} tasks."
    )
    if runtime.exists():
        st.success(f"Plan '{db_plan.title}' and its tasks saved successfully!")
