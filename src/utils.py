import json
from typing import Any, Dict

from loguru import logger
from pydantic import BaseModel
from sqlmodel import TEXT, TypeDecorator


def drop_fields_from_schema(
    json_schema: Dict[str, Any], fields_to_ignore: list[str]
) -> Dict[str, Any]:
    for field in fields_to_ignore:
        del json_schema["properties"][field]
        if field in json_schema["required"]:
            logger.warning(f"Field {field} is required")
            json_schema["required"].remove(field)
    return json_schema


class PydanticSqlModelEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, BaseModel):
            return o.model_dump(mode="json")
        return super().default(o)


class JsonEncodedList(TypeDecorator):
    """Stores and retrieves a list of Pydantic/SQLModel objects as JSON."""

    impl = TEXT  # Store as TEXT in the database
    cache_ok = True  # Important for TypeDecorator

    def __init__(self, item_type, *args, **kwargs):
        """
        item_type: The Pydantic/SQLModel class for items in the list.
        """
        super().__init__(*args, **kwargs)
        self._item_type = item_type

    def process_bind_param(self, value, dialect):
        """
        Called when sending data to the database.
        `value` is the Python list of Pydantic/SQLModel objects.
        """
        if value is None:
            return None
        if not isinstance(value, list):
            raise TypeError("JsonEncodedList expects a list.")

        # Convert each Pydantic/SQLModel object in the list to its dict representation
        # The PydanticSqlModelEncoder will handle the SQLModel instances within the list
        # when json.dumps is called.
        return json.dumps(value, cls=PydanticSqlModelEncoder)

    def process_result_value(self, value, dialect):
        """
        Called when retrieving data from the database.
        `value` is the JSON string from the database.
        """
        if value is None:
            return None
        try:
            list_of_dicts = json.loads(value)
            if not isinstance(list_of_dicts, list):
                # Handle cases where the stored JSON is not a list (e.g., if it was 'null')
                if list_of_dicts is None:
                    return []  # Or None, depending on desired behavior
                raise ValueError("Stored JSON is not a list.")

            # Convert each dict back to a Pydantic/SQLModel object
            return [
                self._item_type.model_validate(item_dict) for item_dict in list_of_dicts
            ]
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(
                f"Error deserializing JSON for {self._item_type.__name__}: {e}, value: {value}"
            )
            # Depending on strictness, you might return an empty list, None, or re-raise
            return []  # Or raise e
