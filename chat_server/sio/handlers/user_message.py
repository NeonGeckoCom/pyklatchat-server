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
from klatchat_utils.database_utils.mongo_utils.queries.dao.prompts import PromptStates
from klatchat_utils.database_utils.mongo_utils.queries.wrapper import (
    MongoDocumentsAPI,
)
from klatchat_utils.database_utils.mongo_utils.structures import MongoFilter
from neon_utils.logger import LOG
from chat_server.sio.server import sio
from chat_server.sio.utils import emit_error, login_required
from chat_server.server_config import server_config
from chat_server.utils.enums import UserRoles
from chat_server.utils.services.popularity_counter import PopularityCounter

from neon_data_models.models.api.klat.socketio import UserMessage


@sio.event
async def user_message(sid, data):
    """
    SIO event fired on new user message in chat
    :param sid: client session id
    :param data: user message data
    """
    LOG.debug(f"Received user message data: {data}")
    try:
        message = UserMessage(**data)
        is_bot = message.is_bot == "1"
        is_proctor = False
        if message.user_id.startswith("neon") and not is_bot:
            neon_data = MongoDocumentsAPI.USERS.get_neon_data(skill_name="neon")
            message.user_id = neon_data["_id"]
        elif is_bot:
            bot_data = MongoDocumentsAPI.USERS.get_bot_data(
                user_id=message.user_id, context=message.context
            )
            message.user_id = bot_data["_id"]
            is_proctor = bot_data["nickname"] == "proctor"

        cid_data = MongoDocumentsAPI.CHATS.get_chat(
            search_str=message.cid,
            column_identifiers=["_id"],
            requested_user_id=message.user_id,
        )
        if not cid_data:
            msg = "Shouting to non-existent conversation, skipping further processing"
            await emit_error(sids=[sid], message=msg)
            return

        audio_path = f"{message.message_id}_audio.wav"
        try:
            if message.is_audio == "1":
                message_text = message.message_body.split(",")[-1]
                server_config.sftp_connector.put_file_object(
                    file_object=message_text, save_to=f"audio/{audio_path}"
                )
                # for audio messages "message_text" references the name of the audio stored
                message.message_body = audio_path
        except Exception as ex:
            LOG.error(f"Failed to located file - {ex}")
            return -1

        is_announcement = message.is_announcement

        if is_announcement == "1":
            if is_proctor and message.prompt_id is not None:
                discussion_counter = message.context.get("discussion_counter")
                if discussion_counter:
                    MongoDocumentsAPI.PROMPTS.update_item(
                        filters=[MongoFilter(key="_id", value=message.prompt_id)],
                        data={"context.discussion_counter": discussion_counter},
                    )
        else:
            is_announcement = "0"

        new_shout_data = message.to_db_query()

        # in case message is received in some foreign language -
        # message text is kept in that language unless English translation received
        if message.lang.split("-")[0] != "en":
            new_shout_data["translations"][message.lang] = message.message_body

        mongo_queries.add_shout(data=new_shout_data)
        if is_announcement == "0" and message.prompt_id is not None:
            if not isinstance(message.prompt_state, PromptStates):
                LOG.error(f"Invalid prompt state: {message.prompt_state}")
                message.prompt_state = PromptStates(message.prompt_state)
            is_ok = MongoDocumentsAPI.PROMPTS.add_shout_to_prompt(
                prompt_id=message.prompt_id,
                user_id=message.user_id,
                message_id=message.message_id,
                prompt_state=message.prompt_state,
            )
            if is_ok:
                prompt_data = MongoDocumentsAPI.PROMPTS.get_item(
                    item_id=message.prompt_id
                )
                new_prompt_data = message.to_new_prompt_message()
                new_prompt_data.context = prompt_data.get("context", {})
                await sio.emit(
                    "new_prompt_message",
                    data=new_prompt_data.model_dump(),
                )

        for language, gender_mapping in message.message_tts.items():
            for gender, audio_data in gender_mapping.items():
                MongoDocumentsAPI.SHOUTS.save_tts_response(
                    shout_id=message.message_id,
                    audio_data=audio_data,
                    lang=language,
                    gender=gender,
                )

        message.bound_service = cid_data.get("bound_service", "")
        # keys_diff = set(data.keys()).difference(set(message.model_dump().keys()))
        # LOG.info(f"Removed keys={keys_diff}")
        LOG.info(
                f"Emitting new_message to client: {message.model_dump()}"
        )
        await sio.emit(
            "new_message", data=message.model_dump(), skip_sid=[sid]
        )
        PopularityCounter.increment_cid_popularity(new_shout_data["cid"])
    except Exception as ex:
        LOG.exception("Socket IO failed to process user message", exc_info=ex)
        await emit_error(
            sids=[sid],
            message=f'Unable to process request "user_message" with data: {data}',
        )


@sio.event
@login_required(min_required_role=UserRoles.ADMIN)
async def broadcast(sid, data):
    """Forwards received broadcast message from client"""
    msg_type = data.pop("msg_type", None)
    msg_receivers = data.pop("to", None)
    if msg_type:
        LOG.debug(f"received broadcast message - {msg_type}")
        await sio.emit(
            msg_type,
            data=data,
            to=msg_receivers,
        )
    else:
        LOG.error("Missing message type attribute", data=data)
