import streamlit as st
from sqlmodel import Session
from src.anki import AnkiCard
from src.db import engine

st.title("Add New Anki Card")

a_content = st.text_input("Side A")
b_content = st.text_input("Side B")

if st.button("Submit") and a_content and b_content:
    with Session(engine) as session:
        card = AnkiCard(a_content=a_content, b_content=b_content)
        session.add(card)
        session.commit()
        st.success("Card added.")
