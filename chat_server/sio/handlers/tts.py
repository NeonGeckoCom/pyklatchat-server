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

from klatchat_utils.common import buffer_to_base64
from klatchat_utils.database_utils.mongo_utils.queries.wrapper import (
    MongoDocumentsAPI,
)
from neon_utils.logger import LOG
from pydantic import ValidationError
from chat_server.sio.server import sio
from chat_server.sio.utils import emit_error
from chat_server.server_config import server_config
from chat_server.utils.languages import LanguageSettings

from neon_data_models.models.api.klat.socketio import (
    GetTtsRequest,
    GetTtsResponse,
)


@sio.event
async def request_tts(sid, data):
    """
    Handles request to Neon TTS service

    :param sid: client session id
    :param data: received tts request data
    """
    try:
        request = GetTtsRequest(sid=sid, **data)
        matching_message = MongoDocumentsAPI.SHOUTS.get_item(item_id=request.message_id)
        if not matching_message:
            LOG.error("Failed to request TTS - matching message not found")
        else:
            # TODO: support for multiple genders in TTS
            # Trying to get existing audio data
            # preferred_gender = (
            #     MongoDocumentsAPI.USERS.get_preferences(user_id=user_id)
            #     .get("tts", {})
            #     .get(lang, {})
            #     .get("gender", "female")
            # )
            preferred_gender = "female"
            audio_file = (
                matching_message.get("audio", {})
                .get(request.lang, {})
                .get(preferred_gender)
            )
            if not audio_file:
                LOG.info(
                    f"File was not detected for cid={request.cid}, message_id={request.message_id}, lang={request.lang}"
                )
                message_text = matching_message.get("message_text")
                formatted_data = {
                    "cid": request.cid,
                    "sid": request.sid,
                    "message_id": request.message_id,
                    "text": message_text,
                    "lang": request.lang,
                }
                await sio.emit("get_tts", data=formatted_data)
            else:
                try:
                    file_location = f"audio/{audio_file}"
                    LOG.info(f"Fetching existing file from: {file_location}")
                    fo = server_config.sftp_connector.get_file_object(file_location)
                    if fo.getbuffer().nbytes > 0:
                        LOG.info(
                            f"File detected for cid={request.cid}, message_id={request.message_id}, lang={request.lang}"
                        )
                        audio_data = buffer_to_base64(fo)
                        response_data = {
                            "cid": request.cid,
                            "message_id": request.message_id,
                            "lang": request.lang,
                            "gender": preferred_gender,
                            "audio_data": audio_data,
                        }
                        await sio.emit("incoming_tts", data=response_data, to=sid)
                    else:
                        LOG.error(
                            f"Empty file detected for cid={request.cid}, message_id={request.message_id}, lang={request.lang}"
                        )
                except Exception as ex:
                    LOG.error(f"Failed to send TTS response - {ex}")
    except ValidationError:
        LOG.exception(f"Invalid TTS request data - {data}")


@sio.event
async def tts_response(sid, data):
    """Handle TTS Response from Observer"""
    response = GetTtsResponse(sid=sid, **data)
    matching_shout = MongoDocumentsAPI.SHOUTS.get_item(item_id=response.message_id)
    if not matching_shout:
        LOG.warning(
            f"Skipping TTS Response for message_id={response.message_id} - matching shout does not exist"
        )
    else:
        if not response.audio_data:
            LOG.warning(
                f"Skipping TTS Response for message_id={response.message_id} - audio data is empty"
            )
        else:
            is_ok = MongoDocumentsAPI.SHOUTS.save_tts_response(
                shout_id=response.message_id,
                audio_data=response.audio_data,
                lang=response.lang,
                gender=response.lang_gender,
            )
            if is_ok:
                response_data = {
                    "cid": response.cid,
                    "message_id": response.message_id,
                    "lang": response.lang,
                    "gender": response.lang_gender,
                    "audio_data": response.audio_data,
                }
                await sio.emit("incoming_tts", data=response_data, to=sid)
            else:
                to = None
                if sid:
                    to = [sid]
                await emit_error(
                    message="Failed to get TTS response",
                    context={
                        "message_id": response.message_id,
                        "cid": response.cid,
                    },
                    sids=to,
                )
