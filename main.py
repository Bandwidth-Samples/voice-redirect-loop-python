import http
import os
import sys
from typing import Union

import bandwidth
from bandwidth.models.bxml import Response as BxmlResponse
from bandwidth.models.bxml import SpeakSentence, Hangup, Ring, Redirect
from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
import uvicorn

try:
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_CLIENT_ID = os.environ['BW_CLIENT_ID']
    BW_CLIENT_SECRET = os.environ['BW_CLIENT_SECRET']
    BASE_CALLBACK_URL = os.environ['BASE_CALLBACK_URL']
    LOCAL_PORT = int(os.environ['LOCAL_PORT'])
except KeyError as e:
    print(f"Please set the environmental variables defined in the README\n\n{e}")
    sys.exit(1)
except ValueError as e:
    print(f"Please set the LOCAL_PORT environmental variable to an integer\n\n{e}")
    sys.exit(1)

app = FastAPI()

bandwidth_configuration = bandwidth.Configuration(
    client_id=BW_CLIENT_ID,
    client_secret=BW_CLIENT_SECRET
)

bandwidth_api_client = bandwidth.ApiClient(bandwidth_configuration)
bandwidth_calls_api_instance = bandwidth.CallsApi(bandwidth_api_client)

active_calls = set()


@app.exception_handler(RequestValidationError)
def invalid_request(request, exc):
    return Response(status_code=http.HTTPStatus.BAD_REQUEST)


@app.post("/callbacks/inbound/voice", status_code=http.HTTPStatus.OK)
def inbound_voice(callback: Union[bandwidth.models.InitiateCallback, bandwidth.models.RedirectCallback]):
    if callback.event_type not in ("initiate", "redirect"):
        print(f"Unexpected event type {callback.event_type} received")
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    if callback.event_type == "initiate":
        active_calls.add(callback.call_id)

    speak_sentence = SpeakSentence(text="Redirecting call, please wait.")
    ring = Ring(duration=30)
    redirect = Redirect(redirect_url="/callbacks/inbound/voice")
    bxml = BxmlResponse([speak_sentence, ring, redirect])

    return Response(content=bxml.to_bxml(), media_type="application/xml")


@app.post("/callbacks/inbound/voice/callEnded", status_code=http.HTTPStatus.OK)
def call_ended(redirect_callback: bandwidth.models.RedirectCallback):
    if redirect_callback.event_type != "redirect":
        print(f"Unexpected event type {redirect_callback.event_type} received")
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    bxml = BxmlResponse([SpeakSentence(text="The call has been ended. Goodbye."), Hangup()])
    return Response(content=bxml.to_bxml(), media_type="application/xml")


@app.post("/callbacks/inbound/voice/disconnect", status_code=http.HTTPStatus.NO_CONTENT)
def disconnect(disconnect_callback: bandwidth.models.DisconnectCallback):
    if disconnect_callback.event_type != "disconnect":
        print(f"Unexpected event type {disconnect_callback.event_type} received")
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    active_calls.discard(disconnect_callback.call_id)
    return Response(status_code=http.HTTPStatus.NO_CONTENT)


@app.get("/calls", status_code=http.HTTPStatus.OK)
def get_calls():
    return list(active_calls)


@app.delete("/calls/{call_id}", status_code=http.HTTPStatus.NO_CONTENT)
def delete_call(call_id: str):
    if call_id not in active_calls:
        return Response(status_code=http.HTTPStatus.NOT_FOUND)

    update_call = bandwidth.UpdateCall(redirect_url=f"{BASE_CALLBACK_URL}/callbacks/inbound/voice/callEnded")

    try:
        bandwidth_calls_api_instance.update_call(BW_ACCOUNT_ID, call_id, update_call)
    except Exception as e:
        print(f"Failed to update call: {e}")
        return Response(status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR)

    active_calls.discard(call_id)
    return Response(status_code=http.HTTPStatus.NO_CONTENT)


if __name__ == "__main__":
    uvicorn.run("main:app", port=LOCAL_PORT, reload=True)
