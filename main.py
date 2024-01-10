from bandwidth.bandwidth_client import BandwidthClient
from bandwidth.voice.models.api_modify_call_request import ApiModifyCallRequest
from bandwidth.voice.bxml.response import Response
from bandwidth.voice.bxml.verbs import *

from flask import Flask, request

import os
import sys
import json

try:
    BW_USERNAME = os.environ['BW_USERNAME']
    BW_PASSWORD = os.environ['BW_PASSWORD']
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_VOICE_APPLICATION_ID = os.environ['BW_VOICE_APPLICATION_ID']
    LOCAL_PORT = os.environ['LOCAL_PORT']
    BASE_CALLBACK_URL = os.environ['BASE_CALLBACK_URL']
except:
    print("Please set the environmental variables defined in the README")
    sys.exit(1)

bandwidth_client = BandwidthClient(
    voice_basic_auth_user_name=BW_USERNAME,
    voice_basic_auth_password=BW_PASSWORD
)

voice_client = bandwidth_client.voice_client.client

app = Flask(__name__)

ACTIVE_CALLS = []

@app.route('/callbacks/inbound', methods=['POST'])
def inbound():
    callback_data = json.loads(request.data)

    if callback_data['eventType'] == 'initiate':
        ACTIVE_CALLS.append(callback_data['callId'])
    
    response = Response()
    if callback_data['eventType'] == 'initiate' or callback_data['eventType'] == 'redirect':
        ring = Ring(
            duration=30
        )
        redirect = Redirect(
            redirect_url='/callbacks/inbound'
        )

        response.add_verb(ring)
        response.add_verb(redirect)
            
    return response.to_bxml()

@app.route('/callbacks/goodbye', methods=['POST'])
def goodbye():
    callback_data = json.loads(request.data)

    response = Response()
    if callback_data['eventType'] == 'redirect':
        speak_sentence = SpeakSentence(
            sentence='The call has been updated. Goodbye'
        )

        response.add_verb(speak_sentence)
            
    return response.to_bxml()

@app.route('/calls/<call_id>', methods=['DELETE'])
def delete_call(call_id):
    if call_id in ACTIVE_CALLS:
        body = ApiModifyCallRequest()
        body.redirect_url = BASE_CALLBACK_URL + "/callbacks/goodbye"
        voice_client.modify_call(BW_ACCOUNT_ID, call_id, body)

        ACTIVE_CALLS.remove(call_id)
        return 'deleted {call_id}'.format(call_id=call_id)
    else:
        return 'call not found', 404

@app.route('/activeCalls', methods=['GET'])
def get_active_calls():
    return json.dumps(ACTIVE_CALLS)

if __name__ == '__main__':
    app.run(port=LOCAL_PORT)
