import http
import json
import os
import sys

import bandwidth
from bandwidth.models.bxml import Response as BxmlResponse
from bandwidth.models.bxml import SpeakSentence, Hangup, Ring, Redirect
from fastapi import FastAPI, Response
from typing import Union
import uvicorn

try:
    BW_USERNAME = os.environ['BW_USERNAME']
    BW_PASSWORD = os.environ['BW_PASSWORD']
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_VOICE_APPLICATION_ID = os.environ['BW_VOICE_APPLICATION_ID']
    BW_NUMBER = os.environ['BW_NUMBER']
    USER_NUMBER = os.environ['USER_NUMBER']
    LOCAL_PORT = int(os.environ['LOCAL_PORT'])
    BASE_CALLBACK_URL = os.environ['BASE_CALLBACK_URL']
except KeyError as e:
    print(f"Please set the environmental variables defined in the README\n\n{e}")
    sys.exit(1)
except ValueError as e:
    print(f"Please set the LOCAL_PORT environmental variable to an integer\n\n{e}")
    sys.exit(1)

app = FastAPI()

bandwidth_configuration = bandwidth.Configuration(
    username=BW_USERNAME,
    password=BW_PASSWORD
)

bandwidth_api_client = bandwidth.ApiClient(bandwidth_configuration)
bandwidth_calls_api_instance = bandwidth.CallsApi(bandwidth_api_client)

active_calls = []


@app.post('/callbacks/inboundCall', status_code=http.HTTPStatus.OK)
def inbound(callback: Union[bandwidth.models.InitiateCallback, bandwidth.models.RedirectCallback]):
    if callback.event_type == "initiate" or callback.event_type == "redirect":
        active_calls.append(callback.call_id)

        speak_sentence = SpeakSentence(text="Redirecting call, please wait.")
        ring = Ring(duration=30)
        redirect = Redirect(redirect_url="/callbacks/redirectedCall")
        bxml = BxmlResponse([speak_sentence, ring, redirect])

        return Response(content=bxml.to_bxml(), media_type="application/xml")
    else:
        speak_sentence = SpeakSentence(text="Invalid event. Hanging up")
        hangup = Hangup()
        bxml = BxmlResponse([speak_sentence, hangup])

        return Response(content=bxml.to_bxml(), media_type="application/xml")


@app.post('/callbacks/callEnded', status_code=http.HTTPStatus.OK)
def goodbye():
    speak_sentence = SpeakSentence(text="The call has been ended. Goodbye.")
    hangup = Hangup()
    bxml = BxmlResponse([speak_sentence, hangup])

    return Response(content=bxml.to_bxml(), media_type="application/xml")


@app.delete('/calls/{call_id}', status_code=http.HTTPStatus.NO_CONTENT)
def delete_call(call_id: str):
    if call_id in active_calls:
        redirect = Redirect(redirect_url="/callbacks/redirectedCall")
        bxml = BxmlResponse([redirect])

        bandwidth_calls_api_instance.update_call_bxml(BW_ACCOUNT_ID, call_id, bxml.to_bxml())
        active_calls.remove(call_id)
        return Response(content=None)
    else:
        return Response(content=None, status_code=http.HTTPStatus.NOT_FOUND)


@app.get('/activeCalls', status_code=http.HTTPStatus.OK)
def get_active_calls():
    data = json.dumps(active_calls)
    return Response(content=data, media_type="application/json")


if __name__ == '__main__':
    uvicorn.run("main:app", port=LOCAL_PORT, reload=True)
