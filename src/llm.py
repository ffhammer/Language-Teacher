from dotenv import load_dotenv
from google import genai
import os
from google.genai import types
from typing import Type, Optional
from pydantic import BaseModel, ValidationError
from ollama import chat

assert load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_KEY"])


def gemini_structured_input(
    system_prompt: str, user_input: str, Schema: Type[BaseModel]
) -> Optional[Type[BaseModel]]:

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_schema=Schema,
            response_mime_type="application/json",
        ),
        contents=user_input,
    )

    return response.parsed


def ollama_structured_input(
    system_prompt: str, user_input: str, Schema: Type[BaseModel]
) -> Optional[BaseModel]:
    """
    Calls Ollama with a structured output schema using the gemma3:12b model.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_input})

    response = chat(
        messages=messages,
        model="gemma3:4b",
        format=Schema.model_json_schema(),
    )

    try:
        return Schema.model_validate_json(response.message.content)
    except ValidationError:
        return None
