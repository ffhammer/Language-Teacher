import streamlit as st
from src.llm import gemini_structured_input, ollama_structured_input
from pydantic import BaseModel, Field
from src.db import engine
from sqlmodel import Session, select
from src.anki import AnkiCard, CardCategory
from typing import Optional
import random

# Styling
st.markdown(
    """
<style>
    .block-container {
        max-width: 700px;
        margin: auto;
        padding-top: 5vh;
    }
    .card-box {
        font-size: 2em;
        text-align: center;
        margin: 2rem 0;
        font-weight: bold;
    }
    .stButton>button {
        background-color: #222;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
    }
    textarea {
        font-size: 1.1em !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Sentence Practice")
category_options = ["All"] + [c.value for c in CardCategory]
selected_category = st.selectbox("Select Card Category", category_options)

st.session_state.setdefault("current_card", None)

if st.session_state.current_card is None:
    with Session(engine) as session:
        statement = select(AnkiCard)

        if selected_category != "All":
            statement = statement.where(AnkiCard.category == selected_category)

        statement = statement.order_by(
            AnkiCard.next_date, AnkiCard.easiness_factor
        ).limit(20)

        results = session.exec(statement).all()
        if results:
            st.session_state.current_card = random.choice(results)
        else:
            st.success("No cards available.")
            st.stop()

card: AnkiCard = st.session_state.current_card

st.markdown(
    f"<div class='card-box'>{card.a_content} – {card.b_content}</div>",
    unsafe_allow_html=True,
)
st.write("Write a sentence using the word above:")

user_input = st.text_area("Your sentence", height=100, key="user_sentence")


class FeedBackMessage(BaseModel):
    correctnes: bool
    explanation: Optional[str] = Field(None)
    corrected_sentence: Optional[str] = None


if st.button("Submit"):
    if not user_input.strip():
        st.warning("Please write a sentence first.")
    else:
        val = ollama_structured_input(
            f"""
            You are a friendly Spanish tutor for absolute beginners.
            The student must write a sentence using the word "{card.a_content}" - "{card.b_content}".
            Evaluate correctness kindly and ignore minor typos or missing accents.
            Give short, helpful feedback if incorrect. Stay BRIEF, no more than one maybe 2 sentences.
            """,
            user_input=user_input,
            Schema=FeedBackMessage,
        )
        if val is None:
            st.error("Sorry, I couldn't evaluate your sentence. Please try again.")
            st.stop()
        st.write("✅ Correct" if val.correctnes else "❌ Incorrect")
        if val.explanation:
            st.write(f"**Explanation**: {val.explanation}")
        if val.corrected_sentence:
            st.write(f"**Suggestion**: {val.corrected_sentence}")

if st.button("Next"):
    st.session_state.current_card = None
    st.session_state.user_input = ""
    st.rerun()
