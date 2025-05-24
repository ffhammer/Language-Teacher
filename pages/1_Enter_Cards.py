import streamlit as st
from sqlmodel import Session

from src.anki import AnkiCard, CardCategory
from src.audio import add_audios_inplance
from src.db import engine

st.title("Add New Anki Card")

a_content = st.text_input("Side A")
b_content = st.text_input("Side B")
category: CardCategory = st.selectbox(
    "Category",
    CardCategory,
)

if st.button("Submit") and a_content and b_content:
    with Session(engine) as session:
        card = AnkiCard(a_content=a_content, b_content=b_content, category=category)
        add_audios_inplance(card)
        session.add(card)
        session.commit()
        st.success("Card added.")
