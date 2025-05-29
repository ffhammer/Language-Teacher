import io
import time
from typing import List

import streamlit as st
from loguru import logger
from pydub import AudioSegment
from pydub.playback import play
from sqlmodel import Field, Relationship, Session
from tqdm import tqdm

from src.anki import AnkiCard, SimpleAnkiCard, update_card
from src.audio import add_audios_inplance
from src.config import INITIAL_PROMPT, LEVEL, SOURCE_LANGUAGE, TARGET_LANGUAGE
from src.db import engine
from src.llm import gemini_structured_ouput

from .base_task import BaseTask


def save_results(cards: list[AnkiCard], results: list[int]) -> None:
    with Session(engine) as sess:
        for card, res in zip(cards, results):
            card = sess.get(AnkiCard, card.id)
            update_card(card, res)
            sess.add(card)
        sess.commit()


class VocabTask(BaseTask, table=True):
    __table_args__ = {"extend_existing": True}

    cards: List[AnkiCard] = Relationship(back_populates="vocab_task")
    b_side_shown: bool = Field(
        True,
        description=(
            "Whether to show the target or source language side first.\n"
            "If False, the easier direction is shown (translation from target to source).\n"
            "If True, the harder direction is shown (translation from source to target)."
        ),
    )

    def display(self, save_anki_results: bool = True):
        if "current_batch" not in st.session_state:
            st.session_state.current_batch = [0, self.cards, []]
            st.session_state.shown = False

        idx, cards, results = st.session_state.current_batch

        if idx < len(cards):
            card: AnkiCard = cards[idx]

            front = card.b_content if self.b_side_shown else card.a_content
            front_audio = card.b_mp3 if self.b_side_shown else card.a_mp3

            back = card.a_content if self.b_side_shown else card.b_content
            back_audio = card.a_mp3 if self.b_side_shown else card.b_mp3

            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"<div class='question-box'>{front}</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                if front_audio:
                    st.audio(front_audio, format="audio/mp3")

            if st.button("Show Answer"):
                st.session_state.shown = not st.session_state.shown

            if st.session_state.get("shown"):
                col3, col4 = st.columns([4, 1])
                with col3:
                    st.markdown(
                        f"<div class='question-box'>{back}</div>",
                        unsafe_allow_html=True,
                    )
                with col4:
                    if back_audio:
                        st.audio(back_audio, format="audio/mp3")
            else:
                # Display an invisible placeholder to keep layout stable
                st.markdown(
                    "<div class='question-box' style='visibility:hidden'>&nbsp;</div>",
                    unsafe_allow_html=True,
                )
            rating = st.slider("How well did you know it?", 0, 5, 3)
            if st.button("Submit Rating"):
                print("submit")
                if back_audio:
                    play(AudioSegment.from_file(io.BytesIO(card.a_mp3), format="mp3"))

                results.append(rating)
                st.session_state.current_batch[0] += 1
                st.markdown(f"You will see the card again in {card.interval} Days")
                time.sleep(0.3)

                # Reset state for next card
                st.session_state.shown = False
                st.session_state.side = "b"  # random.choice(["a", "b"])

                if idx + 1 == len(cards) and save_anki_results:
                    save_results(cards, results)

                st.rerun()

        if st.session_state.get("shown") and card.notes:
            st.markdown(f"Notes:\n{card.notes}")
        st.progress(idx / len(cards))

        if idx == len(cards):
            assert len(cards) == len(results)

            failures: list[AnkiCard] = [
                card for i, card in enumerate(cards) if results[i] == 0
            ]
            success: list[AnkiCard] = [
                card for i, card in enumerate(cards) if results[i]
            ]

            # Results page UI
            st.markdown(
                """
                <div style="text-align:center; margin-top:2rem;">
                    <h1 style="font-size:2.5rem; color:#3B1F0B; font-family:serif; margin-bottom:0.5rem;">
                        Awesome! Continue learning<br>and challenge yourself!
                    </h1>
                    <div style="font-size:1.1rem; color:#7B3F00; margin-bottom:0.5rem;">
                        Answered correctly:
                    </div>
                    <div style="font-size:2.5rem; font-weight:bold; color:#3B1F0B; margin-bottom:2rem;">
                        {}/{}
                    </div>
                </div>
                """.format(len(success), len(cards)),
                unsafe_allow_html=True,
            )

            left, right = st.columns(2)
            with left:
                st.markdown(
                    """
                    <div style="background:#faf8f6; border-radius:18px; padding:1.5rem 1rem; min-height:220px;">
                        <div style="color:#FF4B4B; font-size:1.2rem; font-weight:600; margin-bottom:1rem;">Incorrect</div>
                    """,
                    unsafe_allow_html=True,
                )
                if failures:
                    for card in failures:
                        st.markdown(
                            f"""
                            <div style="background:#fff; border-radius:14px; margin-bottom:0.7rem; padding:0.7rem 1rem; display:flex; align-items:center; gap:10px;">
                                <span style="font-size:1.2rem;">🔊</span>
                                <span style="font-weight:500;">{card.a_content}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        "<div style='color:#888;'>None!</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

            with right:
                st.markdown(
                    """
                    <div style="background:#faf8f6; border-radius:18px; padding:1.5rem 1rem; min-height:220px;">
                        <div style="color:#1CB36B; font-size:1.2rem; font-weight:600; margin-bottom:1rem;">Correct</div>
                    """,
                    unsafe_allow_html=True,
                )
                if success:
                    for card in success:
                        st.markdown(
                            f"""
                            <div style="background:#fff; border-radius:14px; margin-bottom:0.7rem; padding:0.7rem 1rem; display:flex; align-items:center; gap:10px;">
                                <span style="font-size:1.2rem;">🔊</span>
                                <span style="font-weight:500;">{card.a_content}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        "<div style='color:#888;'>None!</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

            description = (
                f"Correct: {', '.join(i.model_dump_json(indent=4, include=['a_content', 'b_content', 'notes']) for i in success) if success else 'None'}\n"
                f"Incorrect: {', '.join(i.model_dump_json(indent=4, include=['a_content', 'b_content', 'notes']) for i in failures) if failures else 'None'}"
            )

            self.result_description = (
                description
                if self.result_description is None
                else self.result_description
                + "\nNew Round of Failures Practice:\n"
                + description
            )

            col1, col2 = st.columns((1, 1))
            with col1:
                if failures:
                    if st.button("Repeat Mistakes"):
                        st.session_state.current_batch = [0, failures, []]
            with col2:
                return st.button("Back to Menu")

    @classmethod
    def generate(
        cls, title: str, generation_instruction: str, purpose: str, timeout: float = 10
    ):
        system_prompt = (
            f"{INITIAL_PROMPT}\n\n"
            "You are generating a vocabulary flashcard task for a student learning "
            f"{TARGET_LANGUAGE} (instruction language: {SOURCE_LANGUAGE}, level: {LEVEL}).\n"
            "Task type: vocab.\n"
            "Description: Vocabulary flashcard tasks, often with spaced repetition, where the learner reviews and rates their knowledge of words or phrases.\n"
            "When to use: Introduce new vocabulary to the user or reinforce previously learned words.\n"
            "You will receive a title, a generation instruction, and a purpose for the task, along with a JSON output schema. "
            "Focus on generating high-quality, level-appropriate vocabulary content based on the provided details. "
            "Ensure the output strictly follows the given schema."
        )
        contents = f"Title: {title}\n\nGeneration Instruction: {generation_instruction}\n\nPurpose: {purpose}"

        cards = gemini_structured_ouput(
            system_prompt=system_prompt,
            contents=contents,
            Schema=list[SimpleAnkiCard],
            timeout=timeout,
        )
        if cards is None:
            return None

        try:
            anki_cards = []
            for card in tqdm(cards, desc="Generating Anki Cards"):
                obj = AnkiCard(**card.model_dump())
                add_audios_inplance(obj)
                anki_cards.append(obj)

            return cls(cards=anki_cards)
        except Exception as e:
            logger.error(f"Generating the Anki Cards failed woth {e}")
