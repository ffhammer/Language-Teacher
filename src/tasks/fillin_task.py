import streamlit as st
from inline_text_fields_component import (
    FullValidationOutput,
    _generate_frontend_segments,
    inline_text_fields,
)
from loguru import logger
from pydantic import (
    computed_field,
    model_validator,
)
from sqlmodel import Column, Field

from src.config import INITIAL_PROMPT, LEVEL, SOURCE_LANGUAGE, TARGET_LANGUAGE
from src.llm import gemini_structured_ouput
from src.utils import JsonEncodedStrList

from .base_task import BaseTask


class FillInTask(BaseTask, table=True):
    """
    Task definition for an inline text fields exercise.
    Users fill in blanks within sentences.
    """

    sentences: list[str] = Field(
        description=(
            "List of sentence rows for the task. Each row has a sentence template."
            "Sentence template with placeholders defined by a delimiter '{}'. "
            "Example: 'The capital of {France} is Paris.)"
        ),
        min_length=1,
        sa_column=Column(JsonEncodedStrList()),
    )
    accepted_levenshtein_distance: int = Field(
        default=0,
        description=(
            "Maximum Levenshtein distance for an answer to be considered 'acceptable' (if not 'perfect'). "
            "A value of 0 means only exact matches (after normalization) are 'perfect'."
        ),
    )

    @computed_field
    @property
    def all_solutions(self) -> list[list[str]]:
        """
        A matrix (list of lists) containing all correct solutions for all fields in all rows.
        Computed using the task's delimiter.
        """
        result = []
        for row in self.sentences:
            vals = []
            for val in _generate_frontend_segments(
                row, start_delimiter="{", end_delimiter="}"
            ):
                if val["type"] == "field":
                    vals.append(val["solution"])
            result.append(vals)
        return result

    @model_validator(mode="after")
    def validate_task_settings_and_rows(self) -> "FillInTask":
        if self.accepted_levenshtein_distance < 0:
            raise ValueError("`accepted_levenshtein_distance` must be non-negative.")

        for row in self.sentences:
            if not row.count("{}"):
                raise ValueError("Missing {}")
            try:
                _generate_frontend_segments(row, start_delimiter="{", end_delimiter="}")
            except Exception:
                raise ValueError(f"Invalid sentence {row}")
        return self

    def display(self, ignore_accents=True) -> bool:
        """
        Displays the inline text fields task in Streamlit and handles user interaction.
        Returns True if the "Next Task" button is clicked, False otherwise.
        """

        st.markdown(f"## {self.title}", unsafe_allow_html=True)
        if self.suptitle:
            st.markdown(self.suptitle, unsafe_allow_html=True)

        # Session state keys, unique per task instance
        freeze_key = f"freeze_inline_{self.id}"
        errors_key = (
            f"errors_inline_{self.id}"  # Stores list of (expected, actual) for errors
        )
        next_task_button_key = f"next_task_inline_{self.id}"

        if freeze_key not in st.session_state:
            st.session_state[freeze_key] = False

        component_output: FullValidationOutput = inline_text_fields(
            sentences_with_solutions=self.sentences,
            ignore_accents=ignore_accents,
            accepted_levenshtein_distance=self.accepted_levenshtein_distance,
            render_results_in_frontend=st.session_state[freeze_key],
            freeze=st.session_state[freeze_key],
            key=f"component_inline_{self.id}",
            # color_kwargs={} # Can be exposed as a task field if needed
        )
        if self.text_below_task:
            st.markdown(self.text_below_task, unsafe_allow_html=True)

        full = all(all(b != "empty" for _, b in res) for res in component_output)

        if not full:
            return
        elif not st.session_state[freeze_key]:
            if st.button("Submit", key=f"submit_inline_{self.id}"):
                st.session_state[freeze_key] = True
                st.session_state[errors_key] = self._get_errors(component_output)
                st.rerun()
            return False

        errors_list = st.session_state.get(errors_key)

        total_fields = sum(len(sols) for sols in self.all_solutions)

        if errors_list is None:
            self.result_description = (
                "An error occurred while evaluating your answers. Please try again."
            )
            st.error(self.result_description)
        elif not errors_list:
            self.result_description = (
                f"Excellent! You answered all {total_fields} fields correctly. 🎉"
            )
            st.success(self.result_description)
        else:  # Some errors
            incorrect_count = len(errors_list)
            correct_count = total_fields - incorrect_count
            error_details_md = "\n".join(
                f"- **Expected:** `{expected}`   **Your answer:** `{user_ans}`"
                for expected, user_ans in errors_list
            )
            self.result_description = (
                f"You answered {correct_count} out of {total_fields} fields correctly.\n\n"
                f"### Incorrect Answers:\n{error_details_md}\n"
            )
            st.markdown(self.result_description, unsafe_allow_html=True)

        return st.button("Next Task", key=next_task_button_key)

    def _get_errors(
        self, component_output: FullValidationOutput
    ) -> list[tuple[str, str]] | None:
        errors: list[tuple[str, str]] = []
        expected_solutions_matrix = self.all_solutions

        if len(component_output) != len(self.sentences):
            logger.error(
                f"Task {self.id or 'N/A'}: Mismatch in number of sentences. "
                f"Component output: {len(component_output)}, Task rows: {len(self.sentences)}."
            )
            return None

        for i, sentence_level_output in enumerate(component_output):
            # These checks protect against malformed data or component bugs
            if i >= len(expected_solutions_matrix):
                logger.warning(
                    f"Task {self.id or 'N/A'}: Sentence index {i} out of bounds for expected_solutions_matrix."
                )
                return None

            solutions_for_this_sentence = expected_solutions_matrix[i]

            if len(sentence_level_output) != len(solutions_for_this_sentence):
                logger.error(
                    f"Task {self.id or 'N/A'}, Sentence {i}: Mismatch in number of fields. "
                    f"Component output fields: {len(sentence_level_output)}, "
                    f"Expected fields: {len(solutions_for_this_sentence)}."
                )
                return None

            for j, (user_input_str, validation_status) in enumerate(
                sentence_level_output
            ):
                if j >= len(solutions_for_this_sentence):
                    logger.warning(
                        f"Task {self.id or 'N/A'}, Sentence {i}: Field index {j} out of bounds for solutions_for_this_sentence."
                    )
                    return None

                expected_solution_str = solutions_for_this_sentence[j]

                if validation_status == "false":
                    errors.append((expected_solution_str, user_input_str))
        return errors

    @classmethod
    def generate(
        cls, title: str, generation_instruction: str, purpose: str, timeout: float = 10
    ):
        system_prompt = (
            f"{INITIAL_PROMPT}\n\n"
            "You are generating a fill-in-the-blank language learning task for a student learning "
            f"{TARGET_LANGUAGE} (instruction language: {SOURCE_LANGUAGE}, level: {LEVEL}).\n"
            "Task type: fill_in.\n"
            "Description: Fill-in-the-blank exercises where the learner types the missing word(s) or letters into a sentence.\n"
            "When to use: Useful for vocabulary recall, grammar points, or testing specific knowledge in context. Use when you want the learner to actively recall and produce language. "
            "Also very good to test if the user conjugates correctly, understands verb tense, or applies correct endings.\n"
            "You will receive a title, a generation instruction, and a purpose for the task, along with a JSON output schema. "
            "Focus on generating high-quality, level-appropriate content based on the provided details. "
            "Ensure the output strictly follows the given schema."
        )
        contents = f"Title: {title}\n\nGeneration Instruction: {generation_instruction}\n\nPurpose: {purpose}"
        return gemini_structured_ouput(
            system_prompt=system_prompt, contents=contents, Schema=cls, timeout=timeout
        )
