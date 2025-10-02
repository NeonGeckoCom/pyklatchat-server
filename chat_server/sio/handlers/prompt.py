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

from klatchat_utils.database_utils.mongo_utils.queries import mongo_queries
from klatchat_utils.database_utils.mongo_utils.queries.wrapper import (
    MongoDocumentsAPI,
)
from neon_utils.logger import LOG
from neon_data_models.models.api.klat.socketio import (
    NewCcaiPrompt,
    CcaiPromptCompleted,
    GetPromptData,
    PromptData,
)
from chat_server.sio.server import sio


@sio.event
async def new_prompt(sid, data):
    """
    SIO event fired on new prompt data saving request
    :param sid: client session id
    :param data: user message data
    """
    prompt = NewCcaiPrompt(**data)
    try:
        formatted_data = prompt.to_db_query()
        MongoDocumentsAPI.PROMPTS.add_item(data=formatted_data)
        await sio.emit("new_prompt_created", data=formatted_data)
    except Exception as ex:
        LOG.error(
            f'Prompt "{prompt.prompt_id}" was not created due to exception - {ex}'
        )


@sio.event
async def prompt_completed(sid, data):
    """
    SIO event fired upon prompt completion
    :param sid: client session id
    :param data: user message data
    """
    prompt = CcaiPromptCompleted(**data)

    LOG.info(f"setting prompt_id={prompt.prompt_id} as completed with: "
             f"{prompt.winner}")
    MongoDocumentsAPI.PROMPTS.set_completed(**prompt.to_db_query())

    keys_diff = set(data.keys()).difference(set(prompt.model_dump().keys()))
    LOG.info(f"Removed keys={keys_diff}")
    await sio.emit("set_prompt_completed", data=prompt.model_dump())


@sio.event
async def get_prompt_data(sid, data):
    """
    SIO event fired getting prompt data request
    :param sid: client session id
    :param data: user message data
    """
    try:
        requested_prompt_data = GetPromptData(**data)
        _prompt_data = PromptData(
            **mongo_queries.fetch_prompt_data(
                **requested_prompt_data.to_db_query()
            )
        )
        if requested_prompt_data.prompt_id:
            # TODO: Confirm this works; unclear what was in `data`
            if isinstance(_prompt_data.data, list):
                prompt_data = _prompt_data.data[0].model_dump()
            else:
                prompt_data = _prompt_data.data.model_dump()
            # prompt_data = {
            #     "_id": _prompt_data[0]["_id"],
            #     "is_completed": _prompt_data[0].get("is_completed", "1"),
            #     **_prompt_data[0].get("data", {}),
            # }
        else:
            prompt_data = []
            if isinstance(_prompt_data.data, list):
                for item in _prompt_data:
                    prompt_data.append(item.model_dump())
                    # prompt_data.append(
                    #     {
                    #         "_id": item["_id"],
                    #         "created_on": item["created_on"],
                    #         "is_completed": item.get("is_completed", "1"),
                    #         **item["data"],
                    #     }
                    # )
        result = dict(
            data=prompt_data,
            receiver=requested_prompt_data.nick,
            cid=requested_prompt_data.cid,
            request_id=requested_prompt_data.request_id,
        )
        LOG.info(f"Emitting prompt_data: {result}")
        await sio.emit("prompt_data", data=result)
    except Exception as ex:
        LOG.error(f"Failed to get prompt data due to exception - {ex}")
