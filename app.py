from bandwidth.bandwidth_client import BandwidthClient
from bandwidth.voice.models.api_modify_call_request import ApiModifyCallRequest
from bandwidth.voice.bxml.response import Response
from bandwidth.voice.bxml.verbs import *

from flask import Flask, request

import os
import sys
import json

try:
    BANDWIDTH_USERNAME = os.environ['BANDWIDTH_USERNAME']
    BANDWIDTH_PASSWORD = os.environ['BANDWIDTH_PASSWORD']
    BANDWIDTH_ACCOUNT_ID = os.environ['BANDWIDTH_ACCOUNT_ID']
    BANDWIDTH_VOICE_APPLICATION_ID = os.environ['BANDWIDTH_VOICE_APPLICATION_ID']
    PORT = os.environ['PORT']
    BASE_URL = os.environ['BASE_URL']
except:
    print("Please set the environmental variables defined in the README")
    sys.exit(1)

bandwidth_client = BandwidthClient(
    voice_basic_auth_user_name=BANDWIDTH_USERNAME,
    voice_basic_auth_password=BANDWIDTH_PASSWORD
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
        body.redirect_url = BASE_URL + "/callbacks/goodbye"
        voice_client.modify_call(BANDWIDTH_ACCOUNT_ID, call_id, body)

        ACTIVE_CALLS.remove(call_id)
        return 'deleted {call_id}'.format(call_id=call_id)
    else:
        return 'call not found', 404

@app.route('/activeCalls', methods=['GET'])
def get_active_calls():
    return json.dumps(ACTIVE_CALLS)

if __name__ == '__main__':
    app.run(port=PORT)
