import re

import streamlit as st
from fill_in_blanks_component import fill_in_blanks
from loguru import logger
from pydantic import BaseModel, Field, computed_field, model_validator


class DragAndDropTaskRow(BaseModel):
    sentence: str = Field(
        description=(
            "Sentence shown to the user. Mark each draggable target with '$'. "
            "Example: 'At what time $does$ your sister dance and how old does she $get$?'"
        )
    )
    distractions: list[str] = Field(
        description="Distractor options, similar to the correct answers.", min_length=1
    )

    @computed_field
    @property
    def stripped_sentence(self) -> str:
        # Replace each $...$ with a single '$'
        return re.sub(r"\$[^$]+\$", "$", self.sentence)

    @computed_field
    @property
    def positives(self) -> list[str]:
        # Extract all text between $...$
        return re.findall(r"\$([^$]+)\$", self.sentence)

    @model_validator(mode="after")
    def check_validity(self) -> "DragAndDropTaskRow":
        if not len(self.positives):
            raise ValueError(
                "No draggable targets (positives) provided in the sentence."
            )
        return self


class DraggingTasks(BaseModel):
    title: str = Field(description="Main title for the task.")
    text_under_title: str | None = Field(
        None,
        description="Optional text shown below the title for context.",
    )
    rows: list[DragAndDropTaskRow] = Field(
        description="List of sentence rows for the task.", min_length=1
    )
    text_task_title: str | None = Field(
        None,
        description="Optional text shown after the main task content.",
    )


def get_errors(
    result: list[dict[int, str]],
    tasks: list[DragAndDropTaskRow],
    options_by_key: dict[str, str],
) -> list[tuple[str, str]] | None:
    try:
        assert len(result) == len(tasks)
        errors = []
        for res, task in zip(result, tasks):
            for i, pos in enumerate(task.positives):
                if options_by_key[res[i]] != pos:
                    errors.append((pos, options_by_key[res[i]]))
        return errors
    except Exception as e:
        logger.exception(f"Failed with {e}")


def dragging_task(config: DraggingTasks, unique_task_key: str) -> bool:
    st.markdown(
        f"## {config.title}", unsafe_allow_html=True, key=f"title_{unique_task_key}"
    )
    if config.text_under_title:
        st.markdown(
            config.text_under_title,
            unsafe_allow_html=True,
            key=f"text_under_title_{unique_task_key}",
        )

    freeze_state = f"freeze_{unique_task_key}"
    if freeze_state not in st.session_state:
        st.session_state[freeze_state] = False
    segments = [task.stripped_sentence for task in config.rows]

    options = []
    options_by_key = {}
    for i, task in enumerate(config.rows):
        for j, pos in enumerate(task.positives):
            options.append({"id": f"row_{i}_pos_{j}", "label": pos})
            options_by_key[f"row_{i}_pos_{j}"] = pos

        for j, neg in enumerate(task.distractions):
            options.append({"id": f"row_{i}_neg_{j}", "label": neg})
            options_by_key[f"row_{i}_neg_{j}"] = neg

    component = fill_in_blanks(
        segments_data=segments,
        options=options,
        freeze=st.session_state[freeze_state],
        key=f"fill_in_{unique_task_key}",
    )
    all_filled = all(all(val is not None for val in dic.values()) for dic in component)

    if not all_filled:
        return False

    errors_key = f"errors_{unique_task_key}"
    if errors_key not in st.session_state:
        if st.button("Submit", key=f"submit_{unique_task_key}"):
            st.session_state[freeze_state] = True
            st.session_state[errors_key] = get_errors(
                result=component, tasks=config.rows, options_by_key=options_by_key
            )
            st.rerun()
    else:
        errors = st.session_state[errors_key]
        if errors is None:
            st.markdown(
                "An unknown error happened sorry.",
                key=f"error_unknown_{unique_task_key}",
            )

        elif not errors:
            st.success("All answers are correct! 🎉", key=f"success_{unique_task_key}")
        else:
            st.markdown(
                "### Incorrect Answers:", key=f"incorrect_header_{unique_task_key}"
            )
            for idx, (correct, user) in enumerate(errors):
                st.markdown(
                    f"- **Expected:** `{correct}` &nbsp;&nbsp; **Your answer:** `{user}`",
                    key=f"incorrect_{unique_task_key}_{idx}",
                )
        return st.button("Next Task", key=f"next_task_{unique_task_key}")
    return False
