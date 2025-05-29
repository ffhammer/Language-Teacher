import streamlit as st
from sqlmodel import SQLModel

from src.anki import CardCategory
from src.db import engine, get_cards_next_cards
from src.llm import ModelUsage  # noqa: F401
from src.plans.plan import ExercisePlan  # noqa: F401
from src.tasks import VocabTask

SQLModel.metadata.create_all(engine)


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

if "current_task" not in st.session_state:
    st.session_state["current_task"] = None

MAX_SESSION_NUMBER = 10


_, center, _ = st.columns([1, 3, 1])
with center:
    if st.session_state.current_task is None:
        st.session_state.select_category = st.selectbox(
            "Select Card Category", category_options
        )
        cards_left = get_cards_next_cards(category=st.session_state.select_category)
        st.write(f"Cards to review: {len(cards_left)}")
        start_new = st.button("Start a Learn Session")

        if start_new:
            st.session_state.current_task = VocabTask(
                id=-1, title="", suptitle="", cards=cards_left[:MAX_SESSION_NUMBER]
            )
            st.rerun()
    else:
        task: VocabTask = st.session_state.current_task
        if task.display(save_anki_results=True):
            st.session_state.current_task = None
            st.rerun()
