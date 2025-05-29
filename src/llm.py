import asyncio
import os
from typing import Optional, Type

from dotenv import load_dotenv
from google import genai
from google.genai import types
from loguru import logger
from ollama import chat
from pydantic import BaseModel, ValidationError

assert load_dotenv()


def retry_n_times(n=3):
    """
    Decorator that retries the decorated function up to n times until it returns a non-None result.
    """

    def decorator(fn):
        def wrapper(*args, **kwargs):
            for attempt in range(n):
                result = fn(*args, **kwargs)
                if result is not None:
                    return result
            return None

        return wrapper

    return decorator


def gemini_text_response(
    system_prompt: str,
    contents,
    model_name: str = "gemini-2.0-flash",
    disable_thinking: bool = False,
    timeout: Optional[float] = None,
):
    config_args = {
        "system_instruction": system_prompt,
    }

    if disable_thinking:
        config_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

    try:

        async def call_gemini():
            client = genai.Client(api_key=os.environ["GEMINI_KEY"])
            return client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(**config_args),
                contents=contents,
            )

        response = asyncio.run(asyncio.wait_for(call_gemini(), timeout=timeout))

        return response.text
    except asyncio.TimeoutError:
        logger.error("Gemini structured input timed out.")
        return None
    except Exception as e:
        logger.error(f"Gemini failed with {e}")
        return None


def gemini_structured_input(
    system_prompt: str,
    contents,
    Schema: Type[BaseModel],
    model_name: str = "gemini-2.0-flash",
    disable_thinking: bool = False,
    timeout: Optional[float] = None,
) -> Optional[BaseModel]:
    config_args = {
        "system_instruction": system_prompt,
        "response_schema": Schema,
        "response_mime_type": "application/json",
    }

    if disable_thinking:
        config_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

    async def call_gemini():
        client = genai.Client(api_key=os.environ["GEMINI_KEY"])
        return client.models.generate_content(
            model=model_name,
            config=types.GenerateContentConfig(**config_args),
            contents=contents,
        )

    try:
        response = asyncio.run(asyncio.wait_for(call_gemini(), timeout=timeout))
        if response is None:
            logger.error("No response received from Gemini structured input.")
            return None
        try:
            return Schema.model_validate_json(response.text)
        except ValidationError as ve:
            logger.error(f"Validation error: {ve}")
            return None
    except asyncio.TimeoutError:
        logger.error("Gemini structured input timed out.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in Gemini structured input: {e}")
        return None


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
