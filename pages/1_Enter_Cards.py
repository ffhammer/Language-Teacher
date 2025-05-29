import json

import markdown
import streamlit as st
from google.genai import types
from loguru import logger
from pdf2image import convert_from_bytes
from pydantic import BaseModel, Field
from streamlit import session_state as state
from tqdm import tqdm

from src.anki import CardCategory, SimpleAnkiCard
from src.db import add_card
from src.llm import gemini_structured_ouput


class ModelAction(BaseModel):
    message_to_user: str = Field(description="The answer message to the user")
    cards_to_add: list[SimpleAnkiCard] = Field(description="The Anki Cards to add")
    cards_to_update: list[SimpleAnkiCard] = Field(
        description="The Anki Cards to update"
    )
    cards_to_delete: list[int] = Field(
        description="The card ids you want to delete for the user"
    )


system_message = """You are helping someone to create new Anki Cards
Target Language: Spanish
BSide Language: German

User Spanish Level: Beginner

You will get messages and images, according to which you should help the user to
add, update or delete there current Anki cards. 

The currents cards are:
{cards_string}

It is important to undestand that above cards are always up to date! 
"""


def to_gemini_content(history: list) -> list:
    contents = []

    for content, speaker in history:
        if speaker == "user":
            contents.append(
                types.Content(role="user", parts=[types.Part(text=content)])
            )
        elif speaker == "bot":
            contents.append(
                types.Content(role="model", parts=[types.Part(text=content)])
            )
        elif speaker == "image":
            ext = content.name.split(".")[-1].lower().replace("jpg", "jpeg")
            contents.append(
                types.Part.from_bytes(
                    data=content.read(),
                    mime_type="application/pdf" if ext == "pdf" else f"image/{ext}",
                )
            )

        else:
            raise ValueError("not implemented")
    return contents


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


def get_reply(history) -> str:
    content = to_gemini_content(history=history)
    cards_string = json.dumps(
        [card.model_dump() for _, card in state.current_cards.items()], indent=4
    )
    logger.debug(system_message.format(cards_string=cards_string))

    try:
        response: ModelAction = gemini_structured_ouput(
            system_prompt=system_message.format(cards_string=cards_string),
            contents=content,
            Schema=ModelAction,
            model_name="gemini-2.5-flash-preview-05-20",
            disable_thinking=True,
        )
        if response is None:
            raise RuntimeError("returnied invalid type")

        for card in response.cards_to_add:
            card.id = max(state.current_cards) + 1 if state.current_cards else 1
            state.current_cards[card.id] = card

        for card in response.cards_to_update:
            if card.id not in state.current_cards:
                logger.warning(f"{card.id} not in cards")
                continue
            logger.debug(f"upadatating {card.model_dump_json(indent=4)}")
            state.current_cards[card.id] = card

        for card_id in response.cards_to_delete:
            state.current_cards.pop(card_id, None)
        logger.debug(f"Got Response:\n{response.model_dump_json(indent=4)}")
        return response.message_to_user
    except Exception as e:
        logger.exception(f"Model Answer failed {e}")

    return "Something wen't wrong. Try again."


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
            if not msg.name.endswith(".pdf"):
                st.image(msg, width=200)
                continue

            for img in convert_from_bytes(msg.read()):
                st.image(img, width=200)

        else:
            st.markdown(
                f'<div class="bot-msg">{markdown.markdown(msg)}</div>',
                unsafe_allow_html=True,
            )

    col1, col2, col3 = st.columns([1, 5, 1])
    with col2:
        user_input = st.text_input(
            "Type your message:",
            key=f"input_{len(state.chat)}",
            label_visibility="collapsed",
        )
        send_btn = st.button("Send")
        if send_btn and user_input:
            state.chat.append((user_input, "user"))

            bot_reply = get_reply(state.chat)
            if bot_reply:
                state.chat.append((bot_reply, "bot"))
            st.rerun()


def render_card_box(card: SimpleAnkiCard, with_del=True):
    cols = st.columns([2, 2, 2, 2, 1])
    card.a_content = cols[0].text_input(
        "Front", value=card.a_content, key=f"a_{card.id}"
    )
    card.b_content = cols[1].text_input(
        "Back", value=card.b_content, key=f"b_{card.id}"
    )
    notes = cols[2].text_input("Notes", value=card.notes, key=f"notes_{card.id}")
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


st.markdown("<br><br>", unsafe_allow_html=True)
_, middle, _ = st.columns([2, 1, 2])

with middle:
    button = st.button("Save Cards")

    if button:
        for _, card in tqdm(state.current_cards.items()):
            card: SimpleAnkiCard
            add_card(
                a_content=card.a_content,
                b_content=card.b_content,
                notes=card.notes,
                category=card.category,
            )

        state.current_cards = {}
        st.rerun()
