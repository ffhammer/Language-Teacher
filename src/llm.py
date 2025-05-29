import asyncio
import os
from datetime import datetime
from typing import Optional, Type

from dotenv import load_dotenv
from google import genai
from google.genai import types
from loguru import logger
from ollama import chat
from pydantic import BaseModel, ValidationError
from sqlmodel import Field, SQLModel

from src.db import Session, engine


class ModelUsage(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(None, primary_key=True)
    model_name: str = Field(index=True)
    usage_time: datetime
    input_tokens: int
    output_tokens: int

    def __repr__(self):
        return f"On {self.usage_time.date()}: {self.model_name} used with input={self.input_tokens}, output={self.output_tokens}"


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
                if attempt + 1 < n:
                    logger.info(f"{fn.__name__} failed. Retrying")
            return None

        return wrapper

    return decorator


def save_model_usage(response, model_name):
    usage = ModelUsage(
        model_name=model_name,
        input_tokens=response.usage_metadata.prompt_token_count,
        output_tokens=response.usage_metadata.candidates_token_count,
        usage_time=datetime.now(),
    )
    if response.usage_metadata.thoughts_token_count:
        usage.output_tokens += response.usage_metadata.thoughts_token_count

    logger.debug(usage.__repr__())
    with Session(engine) as sess:
        sess.add(usage)
        sess.commit()


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
            response = client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(**config_args),
                contents=contents,
            )
            save_model_usage(response, model_name)
            return response

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
        response = client.models.generate_content(
            model=model_name,
            config=types.GenerateContentConfig(**config_args),
            contents=contents,
        )
        save_model_usage(response, model_name)
        return response

    try:
        response = asyncio.run(asyncio.wait_for(call_gemini(), timeout=timeout))
        if not response.parsed:
            raise RuntimeError("No response received from Gemini structured input.")
        return response.parsed
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
