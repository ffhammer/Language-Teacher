import streamlit as st
from src.db import engine
from sqlmodel import Session, select
from src.anki import AnkiCard, update_card
from datetime import date
import random
import time

st.set_page_config(page_title="Anki App", layout="wide")

# CSS to reduce distractions
st.markdown(
    """
<style>
    body {
        background-color: #111;
        color: #eee;
    }
    .block-container {
        max-width: 700px;
        margin: auto;
        padding-top: 5vh;
    }
    .stButton>button {
        background-color: #222;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
    }
    .stSlider > div {
        background-color: #111;
    }
    h1, h2, h3 {
        text-align: center;
    }
    .question-box {
        font-size: 2em;
        text-align: center;
        margin: 2rem 0;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Language Teacher")

with Session(engine) as sess:
    statement = (
        select(AnkiCard)
        .where(AnkiCard.next_date <= date.today())
        .order_by(AnkiCard.easiness_factor)
    )
    cards = list(sess.exec(statement).all())
    st.write(f"Cards to review: {len(cards)}")

    if cards:
        card = cards[0]

        # Use session state to store the current side
        if "side" not in st.session_state:
            st.session_state.side = random.choice(["a", "b"])
            st.session_state.shown = False

        side = st.session_state.side
        front = card.a_content if side == "a" else card.b_content
        back = card.b_content if side == "a" else card.a_content

        st.markdown(f"<div class='question-box'>{front}</div>", unsafe_allow_html=True)

        if st.button("Show Answer"):
            st.session_state.shown = True

        if st.session_state.get("shown"):
            st.markdown(
                f"<div class='question-box'>{back}</div>", unsafe_allow_html=True
            )
        else:
            # Display an invisible placeholder to keep layout stable
            st.markdown(
                "<div class='question-box' style='visibility:hidden'>&nbsp;</div>",
                unsafe_allow_html=True,
            )

        rating = st.slider("How well did you know it?", 0, 5, 3)
        if st.button("Submit Rating"):
            update_card(card, rating)
            st.markdown(f"You will see the card again in {card.interval} Days")
            time.sleep(0.5)
            sess.add(card)
            sess.commit()
            # Reset state for next card
            st.session_state.shown = False
            st.session_state.side = random.choice(["a", "b"])
            st.rerun()
    else:
        st.success("No cards to review today.")
