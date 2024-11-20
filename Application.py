from dotenv import load_dotenv
from flask import Flask, request, session
from flask_cors import CORS
from openai import OpenAI
from prompt_template import template
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Redirect
import os
import uuid

load_dotenv()

Application = Flask(__name__)
CORS(Application)

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
Application.secret_key = os.getenv("APPLICATION_SECRET_KEY")
Api_key = os.getenv("Api_Token")
os.environ["OPENAI_API_KEY"] = os.getenv("OPEN_API")

client = Client(account_sid, auth_token)
client_openai = OpenAI()

@Application.route("/")
def home_route():
    api = request.headers.get("Authorization")
    if api == Api_key:
        return {"message": "Home Route"}
    elif api and api != Api_key:
        return {"message": "Unauthorized Access"}
    else:
        return {"message": "Api key needed"}


@Application.route("/initiate_call")
def call():
    api = request.headers.get("Authorization")
    if api == Api_key:
        call_new = client.calls.create(url="https://3e76-182-187-159-162.ngrok-free.app/answer_query",
                                       to="+923365177871",
                                       from_="+12562428756",
                                       )
        return {"message": f"Call is initiated. Your call id is {str(call_new.sid)}"}
    elif api and api != Api_key:
        return {"message": "Unauthorized Access"}
    else:
        return {"message": "Api key needed"}

@Application.route("/answer_query", methods=["GET", "POST"])
def query():
    # api = request.headers.get("Authorization")
    # if api == Api_key:
    response = VoiceResponse()
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        response.say("Welcome, I am your AI voice assistant. Do you have a question")
        session["call_history"] = [{"role": "system", "content": template}]
        # Instead of "call_history" add str(uuid.uuid4()) to deal with the problem where more than one caller
        # are connected and have separated histories.
    else:
        session["session_id"] = session.get("session_id")
        session["call_history"] = session.get("call_history")
    gather = Gather(input="speech")
    response.append(gather)
    if "SpeechResult" in request.values:
        question = str(request.values["SpeechResult"])
        session["call_history"].append({"role": "user", "content": question})
        if question.lower() in ["goodbye.", "okay, bye.", "okay, goodbye.", "bye."]:
            response.say("Goodbye! Have a nice day")
            # Use response.hangup()
        else:
            completion = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=session["call_history"]
            )
            session["call_history"].append({"role": "assistant",
                                            "content": str(completion.choices[0].message.content)})
            response.say(str(completion.choices[0].message.content))
            response.redirect("/answer_query")
            return str(response)
    else:
        response.say("I could not hear you. Kindly repeat your question")
        response.redirect("/answer_query")
        return str(response)
    session.pop("call_history", None)
    session.pop("session_id", None)
    return str(response)


if __name__ == "__main__":
    Application.run(debug=True)