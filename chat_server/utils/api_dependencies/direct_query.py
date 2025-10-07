"""
Direct query parameter handling for FastAPI endpoints.
"""

from fastapi import Query
from typing import Optional, Type, List
from pydantic import BaseModel

from chat_server.utils.api_dependencies.models import ListPersonasQueryModel


def list_personas_query(
    llms: Optional[List[str]] = Query(None),
    user_id: Optional[str] = Query(None),
    only_enabled: bool = Query(False),
) -> ListPersonasQueryModel:
    """
    Creates a ListPersonasQueryModel from direct query parameters.
    This avoids the issue with FastAPI's dependency injection system.
    """
    return ListPersonasQueryModel(llms=llms, user_id=user_id, only_enabled=only_enabled)
