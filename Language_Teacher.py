import streamlit as st
from src.db import engine
from sqlmodel import Session, select
from src.anki import AnkiCard, update_card, CardCategorie
from datetime import date
import io
import random
import time
from pydub import AudioSegment
from pydub.playback import play

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
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Language Teacher")


# Category selection
category_options = ["All"] + [c.value for c in CardCategorie]
selected_category = st.selectbox("Select Card Category", category_options)

# Initialize repeat_stack in session state
if "repeat_stack" not in st.session_state:
    st.session_state.repeat_stack = []

with Session(engine) as sess:
    statement = select(AnkiCard).where(AnkiCard.next_date <= date.today())
    if selected_category != "All":
        statement = statement.where(AnkiCard.category == selected_category)
    statement = statement.order_by(AnkiCard.easiness_factor)

    cards = list(sess.exec(statement).all())

    # Filter out cards in repeat_stack unless no other cards left
    repeat_stack = st.session_state.repeat_stack
    regular_cards = [c for c in cards if c.id not in repeat_stack]
    if regular_cards:
        card = regular_cards[0]
    elif repeat_stack:
        card = repeat_stack.pop(0)
    else:
        card = None

    st.write(f"Cards to review: {len(cards)}")
    if repeat_stack and not regular_cards:
        st.info(f"Repeating {len(repeat_stack)} difficult card(s)")

    if card:
        # Use session state to store the current side
        if "side" not in st.session_state:
            st.session_state.side = "b"  # random.choice(["a", "b"])
            st.session_state.shown = False

        side = st.session_state.side
        front = card.a_content if side == "a" else card.b_content
        front_audio = card.a_mp3 if side == "a" else card.b_mp3

        back = card.b_content if side == "a" else card.a_content
        back_audio = card.b_mp3 if side == "a" else card.a_mp3

        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"<div class='question-box'>{front}</div>", unsafe_allow_html=True
            )
        with col2:
            if front_audio:
                st.audio(front_audio, format="audio/mp3")

        if st.button("Show Answer"):
            st.session_state.shown = True

        if st.session_state.get("shown"):
            col3, col4 = st.columns([4, 1])
            with col3:
                st.markdown(
                    f"<div class='question-box'>{back}</div>", unsafe_allow_html=True
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
            update_card(card, rating)
            # Play back audio if present (invisible, attempt autoplay)
            if back_audio:
                play(AudioSegment.from_file(io.BytesIO(back_audio), format="mp3"))

            st.markdown(f"You will see the card again in {card.interval} Days")
            time.sleep(0.3)
            sess.add(card)
            sess.commit()
            # If rating is 0, add to repeat_stack if not already present
            if rating == 0 and card.id not in st.session_state.repeat_stack:
                st.session_state.repeat_stack.append(card)

            # Reset state for next card
            st.session_state.shown = False
            st.session_state.side = "b"  # random.choice(["a", "b"])
            st.rerun()
    else:
        st.success("No cards to review today.")
