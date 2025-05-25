import io
import time

import streamlit as st
from pydub import AudioSegment
from pydub.playback import play
from sqlmodel import Session

from src.anki import AnkiCard, CardCategory, update_card
from src.db import engine, get_cards_next_cards

st.set_page_config(page_title="Anki App", layout="wide")

# CSS to reduce distractions
st.markdown(
    f"""
<style>
   {open("style.css").read()}
</style>
""",
    unsafe_allow_html=True,
)

st.title("Language Teacher")


# Category selection
category_options = ["All"] + [c.value for c in CardCategory]
st.session_state.select_category = "All"


if "current_batch" not in st.session_state:
    st.session_state.current_batch = None


def save_results(cards: list[AnkiCard], results: list[int]) -> None:
    with Session(engine) as sess:
        for card, res in zip(cards, results):
            card = sess.get(AnkiCard, card.id)
            update_card(card, res)
            sess.add(card)
        sess.commit()


cards_left = get_cards_next_cards(category=st.session_state.select_category)
st.write(f"Cards to review: {len(cards_left)}")
MAX_SESSION_NUMBER = 10


_, center, _ = st.columns([1, 3, 1])
with center:
    if st.session_state.current_batch is None:
        st.session_state.select_category = st.selectbox(
            "Select Card Category", category_options
        )
        start_new = st.button("Start a Learn Session")

        if start_new:
            st.session_state.current_batch = [0, cards_left[:MAX_SESSION_NUMBER], []]
            st.rerun()
    else:
        idx, cards, results = st.session_state.current_batch

        if idx < len(cards):
            card: AnkiCard = cards[idx]

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
                # Play back audio if present (invisible, attempt autoplay)
                print("submit")
                if back_audio:
                    play(AudioSegment.from_file(io.BytesIO(card.a_mp3), format="mp3"))

                results.append(rating)
                st.session_state.current_batch[0] += 1
                print("new index", st.session_state.current_batch[0], idx)
                st.markdown(f"You will see the card again in {card.interval} Days")
                time.sleep(0.3)

                # Reset state for next card
                st.session_state.shown = False
                st.session_state.side = "b"  # random.choice(["a", "b"])

                if idx + 1 == len(cards):
                    save_results(cards, results)

                st.rerun()
            if st.session_state.get("shown") and card.notes:
                st.markdown(f"Notes:\n{card.notes}")
            st.progress((idx + 1) / min(len(cards), MAX_SESSION_NUMBER))

        if idx == len(cards):
            # in this case we have the results page
            assert len(cards) == len(results)

            failures = [card for i, card in enumerate(cards) if results[i] == 0]
            success = [card for i, card in enumerate(cards) if results[i]]

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

            if st.button("Start Menu"):
                st.session_state.current_batch = None
                st.rerun()

            left, right = st.columns([1, 1])

            with left:
                if failures:
                    if st.button("Repeat Mistakes"):
                        st.session_state.current_batch = [0, failures, []]
            with right:
                if st.button("Start a new Session"):
                    st.session_state.current_batch = [
                        0,
                        cards_left[:MAX_SESSION_NUMBER],
                        [],
                    ]
