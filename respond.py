import os
import re
from flask import Flask, send_file, url_for, request, Blueprint, Response, abort
from twilio.twiml.voice_response import Gather, VoiceResponse, Dial

INTERCOM_BLUEPRINT = Blueprint('intercom', __name__, url_prefix='/intercom')
INTERCOM_APP = Flask(__name__)
ALLOWED_KEYWORDS = [r'liver', r'mail', r'usps', r'ups', r'fedex']
ALLOWED_REGEX = "({})".format(")|(".join(ALLOWED_KEYWORDS))
OPEN_DOOR_DTMF_COMMAND = '6'

def twiml(response):
    response = Response(str(response))
    response.headers['Content-Type'] = 'text/xml'
    return response


def failback():
    response = VoiceResponse()
    response.redirect(
        url_for('intercom.voice', _external=True, _scheme='https'))
    return twiml(response)


@INTERCOM_BLUEPRINT.route('/recording')
def recording():
    type = request.args.get('values')
    if type == "welcome":
        return send_file(os.environ["INTERCOM_RECORDING_WELCOME"])
    elif type == "opened":
        return send_file(os.environ["INTERCOM_RECORDING_OPENED"])
    else:
        abort(404)


@INTERCOM_BLUEPRINT.route('/speech-response', methods=['POST'])
def speech_response():
    speech_response = request.form.get(
        'SpeechResult') or request.form.get('UnstableSpeechResult')
    print(speech_response)
    if speech_response is not None and re.search(ALLOWED_REGEX, speech_response.lower()):
        print("SUCCESS")
        intercom_opened_url = url_for(
            'intercom.recording', values='opened', _external=True, _scheme='https')
        response = VoiceResponse()
        response.play(intercom_opened_url, digits = OPEN_DOOR_DTMF_COMMAND)
        response.hangup()
        return twiml(response)
    return failback()


@INTERCOM_BLUEPRINT.route("/voice", methods=['GET', 'POST'])
def voice():
    speech_reponse_url = url_for(
        'intercom.speech_response', _external=True, _scheme='https')
    print(speech_reponse_url)
    intercom_welcome_url = url_for(
        'intercom.recording', values='welcome', _external=True, _scheme='https')
    response = VoiceResponse()
    with response.gather(action=speech_reponse_url, input='speech', speechTimeout='1') as gather:
        gather.play(intercom_welcome_url)
    dial = Dial()
    dial.dial(os.environ["TENANT_PHONE_NUMBER"])
    response.append(dial)
    return twiml(response)


if __name__ == "__main__":
    INTERCOM_APP.register_blueprint(INTERCOM_BLUEPRINT)
    INTERCOM_APP.run(host='0.0.0.0', port=9092, debug=True)
