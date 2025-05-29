import markdown
import streamlit as st
from loguru import logger
from pdf2image import convert_from_bytes
from streamlit import session_state as state

from src.plans.planning import ChatSpeaker, History_Type, StudyPlan, generate_new_plan
from src.plans.summarize import create_summaries_of_last_plans

st.markdown(
    f"""
<style>
   {open("style.css").read()}
</style>
""",
    unsafe_allow_html=True,
)
if "chat" not in state:
    state.chat = []

if "images" not in state:
    state.images = set()

if "plan" not in state:
    state.plan = StudyPlan.load()
    if state.plan:
        state.chat.append([ChatSpeaker.planning_agent, state.plan])

if state.plan:
    if st.button("Resest Plan"):
        StudyPlan.delete()
        state.plan = None
        state.chat = []
        st.rerun()


if "generating_answers" not in state:
    state.generating_answers = False

_, msg_area, _ = st.columns([1, 3, 1])


def handle_file_upload(uploaded_files):
    file_names = {file.name for file in uploaded_files}
    if file_names != state.images:
        for file_name in file_names.difference(state.images):
            state.images.add(file_name)
            state.chat.append(
                (
                    ChatSpeaker.user_media,
                    next(i for i in uploaded_files if i.name == file_name),
                )
            )

        for file_name in state.images.difference(file_names):
            state.images.remove(file_name)

            state.chat = [
                (a, b)
                for a, b in state.chat
                if a != ChatSpeaker.user_media or b.name != file_name
            ]
        assert file_names == state.images


def render_chat_messages(history: History_Type, from_idx: int = 0):
    speaker_to_class = {
        ChatSpeaker.planning_agent: "bot-msg",
        ChatSpeaker.user: "user-msg",
        ChatSpeaker.summary_agent: "summary-msg",
        ChatSpeaker.critic_agent: "critic-msg",
    }

    if from_idx == 0 and state.plan is None:
        st.markdown(
            f'<div class="{speaker_to_class[ChatSpeaker.planning_agent]}">"Hello, what kind of Plan should I generate?"</div>',
            unsafe_allow_html=True,
        )

    for sender, msg in history[from_idx:]:  # fix: should be from from_idx onward
        if sender == ChatSpeaker.user_media:
            if not msg.name.endswith(".pdf"):
                st.image(msg, width=200)
                continue

            msg.seek(0)  # fix: reset file pointer for PDF
            for img in convert_from_bytes(msg.read()):
                st.image(img, width=200)
            msg.seek(0)  # reset again for future use
            continue

        msg = msg.user_message if sender == ChatSpeaker.planning_agent else msg
        st.markdown(
            f'<div class="{speaker_to_class[sender]}">{markdown.markdown(msg)}</div>',
            unsafe_allow_html=True,
        )


with msg_area:
    uploaded_files = st.file_uploader(
        "Upload a file", type=["png", "jpg", "pdf"], accept_multiple_files=True
    )

    handle_file_upload(uploaded_files)

    st.markdown("<br><br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 5, 1])
    with col2:
        render_chat_messages(state.chat)

        if state.generating_answers:
            start_index = len(state.chat)

            if state.chat and not any(
                sender == ChatSpeaker.summary_agent for sender, _ in state.chat
            ):
                logger.debug("Generating Summary")
                summary = create_summaries_of_last_plans()
                logger.debug(f"Summary:\n{summary}")
                if summary:
                    state.chat.append((ChatSpeaker.summary_agent, summary))

            # fix: generate_new_plan expects history, not an int
            for new_hist, new_plan in generate_new_plan(
                history=state.chat,
            ):
                if new_plan:
                    state.plan = new_plan

                # add only new history piece by piece
                logger.debug(new_hist)
                render_chat_messages(new_hist, from_idx=start_index)

                state.chat = new_hist
                start_index = len(state.chat)

            # reset flags
            state.generating_answers = False
            state.input = ""

        user_input = st.text_input(
            "Type your message:", key="input", label_visibility="collapsed"
        )
        send_btn = st.button("Send")
        if send_btn and user_input:
            state.chat.append((ChatSpeaker.user, user_input))
            state.generating_answers = True
            st.rerun()

    if state.plan:
        plan: StudyPlan = state.plan
        plan.display()

        if st.button("Save"):
            plan.save()
