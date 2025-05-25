import os
from typing import Optional, Type

from dotenv import load_dotenv
from google import genai
from google.genai import types
from ollama import chat
from pydantic import BaseModel, ValidationError

assert load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_KEY"])


def gemini_structured_input(
    system_prompt: str,
    contents,
    Schema: Type[BaseModel],
    model_name: str = "gemini-2.0-flash",
    disable_thinking: bool = False,
) -> Optional[Type[BaseModel]]:
    config_args = {
        "system_instruction": system_prompt,
        "response_schema": Schema,
        "response_mime_type": "application/json",
    }

    if disable_thinking:
        config_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

    response = client.models.generate_content(
        model=model_name,
        config=types.GenerateContentConfig(**config_args),
        contents=contents,
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
