import re

import streamlit as st
from fill_in_blanks_component import fill_in_blanks
from loguru import logger
from pydantic import BaseModel, computed_field, model_validator
from sqlmodel import Column, Field

from src.utils import JsonEncodedListofBaseModels

from .base_task import BaseTask


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
        return re.findall(r"\$([^$]+)\$", self.sentence)

    @model_validator(mode="after")
    def check_validity(self) -> "DragAndDropTaskRow":
        if not len(self.positives):
            raise ValueError(
                "No draggable targets (positives) provided in the sentence."
            )
        return self


class DraggingTask(BaseTask, table=True):
    rows: list[DragAndDropTaskRow] = Field(
        description="List of sentence rows for the task.",
        min_length=1,
        sa_column=Column(JsonEncodedListofBaseModels(item_type=DragAndDropTaskRow)),
    )

    def display(self) -> bool:
        st.markdown(f"## {self.title}", unsafe_allow_html=True)
        if self.suptitle:
            st.markdown(
                self.suptitle,
                unsafe_allow_html=True,
            )

        freeze_state = f"freeze_{self.id}"
        if freeze_state not in st.session_state:
            st.session_state[freeze_state] = False
        segments = [task.stripped_sentence for task in self.rows]

        options = []
        options_by_key = {}
        for i, task in enumerate(self.rows):
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
            key=f"fill_in_{self.id}",
        )
        all_filled = all(
            all(val is not None for val in dic.values()) for dic in component
        )

        if not all_filled:
            return False

        errors_key = f"errors_{self.id}"
        if errors_key not in st.session_state:
            if st.button("Submit", key=f"submit_{self.id}"):
                st.session_state[freeze_state] = True
                st.session_state[errors_key] = self._get_errors(
                    result=component, options_by_key=options_by_key
                )
                st.rerun()
        else:
            errors = st.session_state[errors_key]

            # Prepare result_description with detailed feedback, but only show summary via st.success
            total = sum(len(task.positives) for task in self.rows)
            incorrect = len(errors) if errors else 0
            correct = total - incorrect

            if errors is None:
                self.result_description = (
                    "An unknown error occurred while evaluating your answers."
                )
            elif not errors:
                self.result_description = (
                    "Excellent! You answered all everything correctly 🎉"
                )
            else:
                details = "\n".join(
                    f"- **Expected:** `{correct}` &nbsp;&nbsp; **Your answer:** `{user}`"
                    for correct, user in errors
                )
                self.result_description = (
                    f"You answered {correct} out of {total} blanks correctly.\n\n"
                    f"### Incorrect Answers:\n{details}\n"
                )

            (
                st.success(self.result_description)
                if not errors
                else st.markdown(self.result_description)
            )

            return st.button("Next Task", key=f"next_task_{self.id}")
        return False

    def _get_errors(
        self,
        result: list[dict[int, str]],
        options_by_key: dict[str, str],
    ) -> list[tuple[str, str]] | None:
        try:
            assert len(result) == len(self.rows)
            errors = []
            for res, task in zip(result, self.rows):
                for i, pos in enumerate(task.positives):
                    if options_by_key[res[i]] != pos:
                        errors.append((pos, options_by_key[res[i]]))
            return errors
        except Exception as e:
            logger.exception(f"Failed with {e}")
