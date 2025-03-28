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

from typing import Type

from fastapi import Depends
from pydantic import BaseModel

from chat_server.utils.http_exceptions import UserUnauthorizedException
from chat_server.utils.api_dependencies.extractors import CurrentUserData
from chat_server.utils.enums import UserRoles, RequestModelType


def permitted_access(
    model_type: Type[BaseModel],
    min_required_role: UserRoles = UserRoles.GUEST,
    request_model_type: RequestModelType = RequestModelType.QUERY,
):
    """
    Dependency called for Fast API request models to verify if it can be accessed by the requested user
    :param model_type: arbitrary model type inherited from pydantic.BaseModel
    :param min_required_role: minimal required role to consider from UserRoles
    :param request_model_type: type of the API handler (default RequestModelType.QUERY)
    :return: Validated model
    :raises UserUnauthorizedException: if the user is not authorized to access the endpoint
    """
    return Depends(
        _validate_api_access(model_type, min_required_role, request_model_type)
    )


def _validate_api_access(
    model_type: Type[BaseModel],
    min_required_role: UserRoles = UserRoles.AUTHORIZED_USER,
    request_model_type: RequestModelType = RequestModelType.QUERY,
) -> BaseModel:
    """
    Checks if provided to current user model and is authorized to perform actions on behalf of the target user data
    """

    if request_model_type == RequestModelType.QUERY:
        default_value = Depends()
    else:
        default_value = None

    async def permission_dependency_checker(
        current_user: CurrentUserData, request_model: model_type = default_value
    ):
        is_authorized = _check_is_authorized(
            current_user=current_user,
            request_model=request_model,
            min_required_role=min_required_role,
        )
        if not is_authorized:
            raise UserUnauthorizedException
        return request_model

    return permission_dependency_checker


def _check_is_authorized(
    current_user: CurrentUserData,
    request_model: BaseModel,
    min_required_role: UserRoles,
) -> bool:
    """
    Runs check if current user if authorized to perform actions on behalf of the model
    :param current_user: Current user data model
    :param request_model: Provided Request Model
    :param min_required_role: minimal required role to consider from UserRoles
    :return:
    """
    is_authorized = True
    if min_required_role > UserRoles.GUEST and current_user.is_tmp:
        return False
    if user_id := getattr(request_model, "user_id", None):
        min_required_role, is_authorized = _is_authorized_by_model_attributes(
            user_id=user_id,
            min_required_role=min_required_role,
            current_user=current_user,
        )
    if not is_authorized:
        is_authorized |= has_admin_role(
            current_user=current_user, min_required_role=min_required_role
        )
    return is_authorized


def _is_authorized_by_model_attributes(
    user_id: str, current_user: CurrentUserData, min_required_role: UserRoles
) -> tuple[UserRoles, bool]:
    """
    Checks if current user model is authorized target user id contained in request model
    :param user_id: "user_id" attribute of request model
    :param current_user: current user data model
    :param min_required_role: minimal required role to consider from UserRoles
    :return: tuple contains of two items: actual minimal required role (could be recalculated based on user_id value)
             and state of authorization flag
    """
    is_authorized = False
    if user_id == "*":
        min_required_role = UserRoles.ADMIN
    else:
        is_authorized |= current_user.user_id == user_id
    return min_required_role, is_authorized


def has_admin_role(
    current_user: CurrentUserData, min_required_role: UserRoles = UserRoles.ADMIN
) -> bool:
    """
    Checks if current user model is authorized to request endpoint based on admin role
    :param current_user: current user data model
    :param min_required_role: minimal required role to consider from UserRoles
    :return: True if current user model is authorized to request endpoint based on admin role else False
    """
    min_required_role = max(min_required_role, UserRoles.ADMIN)
    allowed_roles = set(
        role.name.lower() for role in UserRoles if role >= min_required_role
    )
    matching_roles_subset = set(current_user.roles).intersection(allowed_roles)
    return len(matching_roles_subset) > 0


def get_authorized_user(current_user: CurrentUserData):
    """
    Fast API Dependency ensuring that caller is authorized user on Klat Server
    :param current_user: current user data model
    :return: current user data model
    :raises UserUnauthorizedException: if the user is not authorized to access the endpoint
    """
    if current_user.is_tmp:
        raise UserUnauthorizedException
    return current_user
