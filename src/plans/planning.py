import os
from enum import Enum, StrEnum
from typing import Any, Generator, Optional

import streamlit as st
from google.genai import types
from loguru import logger
from pydantic import BaseModel, Field

from src.config import INITIAL_PROMPT, SOURCE_LANGUAGE, TARGET_LANGUAGE
from src.llm import gemini_structured_ouput, retry_n_times


class TaskCategories(StrEnum):
    DRAG_AND_DROP = "drag_and_drop"
    FILL_IN = "fill_in"
    SENTENCE_ORDER = "sentence_order"
    VOCAB = "vocab"


class Task(BaseModel):
    category: TaskCategories
    title: str = Field(description="The Title of the task")
    generation_instruction: str = Field(
        description="Description for the task generation agent on what kind of content to include"
    )
    purpose: str = Field(description="The purpose of the task")


class StudyPlan(BaseModel):
    user_message: str = Field(
        description="The reply that will be shown in the Chat interface to the user."
    )
    title: str = Field(description="The title of the study Plan")
    goal: str = Field(description="The goal of current study plan")
    tasks: list[Task] = Field(min_length=1, description="The tasks to be generated")

    def display(self):
        st.markdown(f"## {self.title}")
        st.markdown(f"### Goal\n{self.goal}")
        st.markdown("---")
        st.markdown("### Tasks")
        for i, task in enumerate(self.tasks, 1):
            st.markdown(
                f"""
                <div style="background:#f9f9f9; border-radius:10px; padding:1rem; margin-bottom:1rem;">
                    <b>Task {i}: {task.title}</b>  
                    <ul>
                        <li><b>Type:</b> {task.category.value.replace("_", " ").title()}</li>
                        <li><b>Purpose:</b> {task.purpose}</li>
                        <li><b>Generation Instruction:</b> {task.generation_instruction}</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    def save(self):
        with open("study_plan.json", "w") as f:
            f.write(self.model_dump_json(indent=4))

    @classmethod
    def load(cls) -> Optional["StudyPlan"]:
        if not os.path.exists("study_plan.json"):
            return
        with open("study_plan.json", "r") as f:
            return cls.model_validate_json(f.read())

    @classmethod
    def delete(cls) -> Optional["StudyPlan"]:
        if not os.path.exists("study_plan.json"):
            logger.warning("Study Plan does not exist -> null op")
            return
        os.remove("study_plan.json")


PLANNER_PROMPT = f"""
{INITIAL_PROMPT}
Your job is to help the user plan a new study plan. Listen to what the user wants and create tasks accordingly.
Initially, you will get an optional summary of the user's past performance so you can create tailored exercises,
especially regarding their weaknesses.

Optionally, there may be a critic agent criticizing your work; please try to address its criticisms.

The kinds of tasks available, their descriptions, and when to use them:

- drag_and_drop: 
    Description: Sentence-based tasks where the learner drags and drops words or phrases into blanks to complete a sentence.
    When to use: Great for practicing word order, grammar, and sentence structure. Use when the goal is to reinforce syntax or test understanding of sentence construction.
    Also great when the user needs to choose the specific form of a verb, adjective, or pronoun.

- fill_in: 
    Description: Fill-in-the-blank exercises where the learner types the missing word(s) or letters into a sentence.
    When to use: Useful for vocabulary recall, grammar points, or testing specific knowledge in context. Use when you want the learner to actively recall and produce language.
    Also very good to test if the user conjugates correctly, understands verb tense, or applies correct endings.

- sentence_order: 
    Description: The learner is given a sentence in {SOURCE_LANGUAGE} and words in {TARGET_LANGUAGE} along with some distraction words. The user must reorder the words to form a correct sentence.
    When to use: Ideal for translation, sentence structure, word order, and understanding how sentences are formed in the target language.

- vocab: 
    Description: Vocabulary flashcard tasks, often with spaced repetition, where the learner reviews and rates their knowledge of words or phrases.
    When to use: Introduce new vocabulary to the user or reinforce previously learned words.
"""


CRITIC_PROMPT = f"""
{INITIAL_PROMPT}
Your role is to act as the Planning Stage Critic. You will receive messages from the User, the Summary Agent, and most importantly, the Planning Agent.
Your job is to evaluate whether the plan proposed by the Planning Agent is effective and appropriate for the student's needs. If you identify any issues, gaps, or areas for improvement, provide clear and constructive feedback to help refine the plan.

Consider the following when reviewing the plan:
- Are the tasks well-aligned with the student's goals and proficiency level?
- Is there a good variety of task types to address different skills (e.g., grammar, vocabulary, sentence structure)?
- Are the instructions and purposes for each task clear and actionable?
- Does the plan address any weaknesses or areas for improvement mentioned in the user's summary or previous performance?
- Is the overall progression logical and supportive of the student's learning journey?

Below are the available task types, their descriptions, and when to use them:

- drag_and_drop: 
    Description: Sentence-based tasks where the learner drags and drops words or phrases into blanks to complete a sentence.
    When to use: Great for practicing word order, grammar, and sentence structure. Use when the goal is to reinforce syntax or test understanding of sentence construction.
    Also great when the user needs to choose the specific form of a verb, adjective, or pronoun.

- fill_in: 
    Description: Fill-in-the-blank exercises where the learner types the missing word(s) or letters into a sentence.
    When to use: Useful for vocabulary recall, grammar points, or testing specific knowledge in context. Use when you want the learner to actively recall and produce language.
    Also very good to test if the user conjugates correctly, understands verb tense, or applies correct endings.

- sentence_order: 
    Description: The learner is given a sentence in {SOURCE_LANGUAGE} and words in {TARGET_LANGUAGE} along with some distraction words. The user must reorder the words to form a correct sentence.
    When to use: Ideal for translation, sentence structure, word order, and understanding how sentences are formed in the target language.

- vocab: 
    Description: Vocabulary flashcard tasks, often with spaced repetition, where the learner reviews and rates their knowledge of words or phrases.
    When to use: Introduce new vocabulary to the user or reinforce previously learned words.

If the plan is strong and well-constructed, acknowledge its give a green flag. If not, provide specific suggestions for improvement.
"""


class CriticOutput(BaseModel):
    is_good_enough: bool = Field(description="Whether plan can be given to the user")
    criticism: None | str = Field(
        description="If not good enough, that will be the criticism for the Planning Agent"
    )


class ChatSpeaker(Enum):
    user = 0
    planning_agent = 1
    critic_agent = 2  # fix: spelling
    summary_agent = 3
    user_media = 4
    last_plan = 5


History_Type = list[tuple[ChatSpeaker, Any]]


def to_gemini_content(history: History_Type) -> list:
    contents = []

    for speaker, content in history:
        if speaker == ChatSpeaker.user:
            contents.append(
                types.Content(role="user", parts=[types.Part(text=content)])
            )
        elif speaker == ChatSpeaker.planning_agent:
            contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=f"Planning Agent:\n{content.model_dump_json(indent=4)}"
                        )
                    ],
                )
            )
        elif speaker == ChatSpeaker.critic_agent:
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part(text=f"Critic Agent:\n{content}")],
                )
            )
        elif speaker == ChatSpeaker.summary_agent:
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part(text=f"Summary Agent:\n{content}")],
                )
            )
        elif speaker == ChatSpeaker.user_media:
            ext = content.name.split(".")[-1].lower().replace("jpg", "jpeg")
            content.seek(0)  # fix: reset pointer before reading
            contents.append(
                types.Part.from_bytes(
                    data=content.read(),
                    mime_type="application/pdf" if ext == "pdf" else f"image/{ext}",
                )
            )
            content.seek(0)  # reset pointer after reading
        else:
            raise ValueError("not implemented")
    return contents


def generate_new_plan(
    history: History_Type,
    n_times_critism=1,
    retries=1,
) -> Generator[tuple[History_Type, StudyPlan | None], Any, Any]:
    plan: StudyPlan = retry_n_times(n=retries)(gemini_structured_ouput)(
        PLANNER_PROMPT, to_gemini_content(history), StudyPlan, timeout=15
    )

    if plan is None:
        history.append(
            (
                ChatSpeaker.planning_agent,
                "We have a failure, try again",
            )
        )
        yield history, None
        return

    history.append((ChatSpeaker.planning_agent, plan))
    yield history, plan

    for n in range(n_times_critism):
        criticsm: CriticOutput = retry_n_times(n=retries)(gemini_structured_ouput)(
            CRITIC_PROMPT, to_gemini_content(history), CriticOutput, timeout=15
        )

        if criticsm is None:
            history.append((ChatSpeaker.critic_agent, "Failed to criticize"))
            yield history, plan
            continue

        if criticsm.is_good_enough:
            history.append((ChatSpeaker.critic_agent, "Looks good (:"))
            yield history, plan
            continue

        history.append((ChatSpeaker.critic_agent, criticsm.criticism))
        new_plan = retry_n_times(n=retries)(gemini_structured_ouput)(
            PLANNER_PROMPT, to_gemini_content(history), StudyPlan, timeout=15
        )
        if new_plan is None:
            history.append(
                (
                    ChatSpeaker.planning_agent,
                    "We have a failure, try again",
                )
            )
            yield history, plan
            continue

        plan = new_plan
        history.append((ChatSpeaker.planning_agent, plan))
        yield history, plan
