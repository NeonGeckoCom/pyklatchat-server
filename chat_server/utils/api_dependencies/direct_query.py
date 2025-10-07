# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from fastapi import Query, Path, Body
from typing import Optional, List

from chat_server.utils.api_dependencies.models import (
    ListPersonasQueryModel,
    AddPersonaModel,
    SetPersonaModel,
    DeletePersonaModel,
    TogglePersonaStatusModel,
)
from chat_server.utils.api_dependencies.models.personas import PersonaModel
from chat_server.utils.api_dependencies.extractors.personas import PersonaData


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


def get_persona_query(
    persona_id: str = Path(..., description="ID of the persona to retrieve"),
) -> PersonaModel:
    """
    Creates a PersonaModel from a path parameter.
    """
    return PersonaData(persona_id)


def add_persona_body(
    persona_name: str = Body(...),
    user_id: Optional[str] = Body(None),
    supported_llms: List[str] = Body(default=[]),
    default_llm: Optional[str] = Body(None),
    description: str = Body(...),
    enabled: bool = Body(False),
) -> AddPersonaModel:
    """
    Creates an AddPersonaModel from body parameters.
    """
    return AddPersonaModel(
        persona_name=persona_name,
        user_id=user_id,
        supported_llms=supported_llms,
        default_llm=default_llm,
        description=description,
        enabled=enabled,
    )


def set_persona_body(
    persona_name: str = Body(...),
    user_id: Optional[str] = Body(None),
    supported_llms: List[str] = Body(default=[]),
    default_llm: Optional[str] = Body(None),
    description: str = Body(...),
) -> SetPersonaModel:
    """
    Creates a SetPersonaModel from body parameters.
    """
    return SetPersonaModel(
        persona_name=persona_name,
        user_id=user_id,
        supported_llms=supported_llms,
        default_llm=default_llm,
        description=description,
    )


def delete_persona_query(
    persona_name: str = Query(...),
    user_id: Optional[str] = Query(None),
) -> DeletePersonaModel:
    """
    Creates a DeletePersonaModel from query parameters.
    """
    return DeletePersonaModel(
        persona_name=persona_name,
        user_id=user_id,
    )


def toggle_persona_body(
    persona_name: str = Body(...),
    user_id: Optional[str] = Body(None),
    enabled: bool = Body(True),
) -> TogglePersonaStatusModel:
    """
    Creates a TogglePersonaStatusModel from body parameters.
    """
    return TogglePersonaStatusModel(
        persona_name=persona_name,
        user_id=user_id,
        enabled=enabled,
    )
