from typing import Optional

import streamlit as st
from pydantic import BaseModel, Field
from streamlit import session_state as state

from src.anki import CardCategory


class SimpleAnkiCard(BaseModel):
    a_content: str = Field(description="The Content of one site")
    b_content: str = Field(description="The Content of translation/other site")
    category: CardCategory
    notes: Optional[str] = Field(
        None, description="Optional notes and context or examples"
    )
    id: Optional[int] = Field(
        None,
        description="When generating a new card, keep this as None!. When updating, use the specific id",
    )


class ModelAction(BaseModel):
    message_to_user: str = Field(description="The answer message to the user")
    add_or_update: list[SimpleAnkiCard] = Field(
        description="The Anki Cards to add or Update"
    )
    cards_to_delete: list[int] = Field(
        description="The card ids you want to delete for the user"
    )


st.markdown(
    f"""
<style>
   {open("style.css").read()}
</style>
""",
    unsafe_allow_html=True,
)
if "chat" not in state:
    state.chat = [
        ("Hello, how are you?", "bot")
    ]  # either (str, bot), (str, user), (image, image)

if "images" not in state:
    state.images = set()

if "current_cards" not in state:
    state.current_cards = {}


_, msg_area, _ = st.columns([1, 3, 1])
with msg_area:
    uploaded_files = st.file_uploader(
        "Upload a file", type=["png", "jpg", "pdf"], accept_multiple_files=True
    )

    file_names = {file.name for file in uploaded_files}
    if file_names != state.images:
        for file_name in file_names.difference(state.images):
            state.images.add(file_name)
            state.chat.append(
                (next(i for i in uploaded_files if i.name == file_name), "image")
            )

        for file_name in state.images.difference(file_names):
            state.images.remove(file_name)

            state.chat = [
                (a, b) for a, b in state.chat if b != "image" or a.name != file_name
            ]
        assert file_names == state.images

    st.markdown("<br><br>", unsafe_allow_html=True)
    for msg, sender in state.chat:
        if sender == "user":
            st.markdown(f'<div class="user-msg">{msg}</div>', unsafe_allow_html=True)
        elif sender == "image":
            st.image(msg, width=200)
        else:
            st.markdown(f'<div class="bot-msg">{msg}</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 5, 1])
    with col2:
        user_input = st.text_input(
            "Type your message:", key="input", label_visibility="collapsed"
        )
        send_btn = st.button("Send")
        if send_btn and user_input:
            state.chat.append((user_input, "user"))
            # Example: bot wants to present options
            if "image" in user_input.lower():
                bot_reply = "Would you like to upload a picture or skip?"
                state.chat.append((bot_reply, "bot"))
                state.next_action = "ask_upload"
            else:
                bot_reply = "This is the bot's response to: " + user_input
                state.chat.append((bot_reply, "bot"))
                state.next_action = None
            st.rerun()


def render_card_box(card: SimpleAnkiCard, with_del=True):
    cols = st.columns([2, 2, 2, 2, 1])
    card.a_content = cols[0].text_input(
        "Front", value=card.a_content, key=f"a_{card.id}"
    )
    card.b_content = cols[1].text_input(
        "Back", value=card.b_content, key=f"b_{card.id}"
    )
    notes = cols[2].text_input("Notes", key=f"notes_{card.id}")
    card.notes = notes if notes else None

    card.category = cols[3].selectbox(
        "Category",
        CardCategory,
        index=list(CardCategory).index(card.category),
        key=f"cat_{card.id}",
    )
    if cols[4].button("Save", key=f"save_{card.id}"):
        state.current_cards[card.id] = card
        st.rerun()
    if with_del and cols[4].button("Delete", key=f"del_{card.id}"):
        state.current_cards.pop(card.id)
        st.rerun()


st.markdown("<br><br>", unsafe_allow_html=True)
for _, card in state.current_cards.items():
    render_card_box(card)

# empy card
additional_card = SimpleAnkiCard(
    id=max(state.current_cards) + 1 if state.current_cards else 1,
    a_content="",
    b_content="",
    category=CardCategory.adjective,
)
render_card_box(additional_card, with_del=False)
