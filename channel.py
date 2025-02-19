## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests
from better_profanity import profanity #for filtering
from flask_cors import CORS
import datetime

#load the defult list of th bad words
profanity.load_censor_words()

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """
    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!' # change to something random, no matter what

# Create Flask app
app = Flask(__name__)
CORS(app)       #enable CORS for all routes
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

#Channel settings:
HUB_URL = 'http://vm146.rz.uni-osnabrueck.de/hub'
HUB_AUTHKEY = 'Crr-K24d-2N'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "The one and only Football Channel"
CHANNEL_ENDPOINT = "http://vm146.rz.uni-osnabrueck.de/u033/channel.wsgi" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

#simple welcome message to insert if the file is empty
WELCOME_MESSAGE = {
    'content' : "Welcome to the greatest place to talk about Football!",
    'sender' : "System",
    'timestamp' : "2025-02-16T00:00:00",
    'extra' : None
}
#off-toppic words to filter out
OFF_TOPIC_KEYWORDS = ["cooking", "recipe", "politics", "movie", "economy"]

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(
        HUB_URL + '/channels',
        headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
        data=json.dumps({
            "name": CHANNEL_NAME,
            "endpoint": CHANNEL_ENDPOINT,
            "authkey": CHANNEL_AUTHKEY,
            "type_of_service": CHANNEL_TYPE_OF_SERVICE,
        })
    )

    if response.status_code != 200:
        print("Error creating channel: ", response.status_code, response.text)
    else:
        print("Channel registered or updated successfully.")


def check_authorization(req):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in req.headers:
        return False
    return req.headers['Authorization'] == 'authkey ' + CHANNEL_AUTHKEY


@app.route('/health', methods=['GET'])
def health_check():
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name': CHANNEL_NAME}), 200

# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    # return all messages in JSON
    return jsonify(read_messages())

# POST: Send a message
@app.route('/', methods=['POST'])
def send_message():
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if 'content' not in message:
        return "No content", 400
    if 'sender' not in message:
        return "No sender", 400
    if 'timestamp' not in message:
        return "No timestamp", 400
    

    original_content = message['content']

    #off-topic filtering
    if is_off_topic(original_content):
        return "Off-topic: This channel only welcomes Football discussions. Message blocked.", 400
    
    #profanity filter
    cleaned_content = profanity.censor(original_content) # e.g. "****" for bad words
    # Save the sanitized content
    message['content'] = cleaned_content
    #save incoming message
    messages = read_messages()
    messages.append({
        'content' : message['content'],
        'sender' : message['sender'],
        'timestamp' : message['timestamp'],
        'extra' : message.get('extra', None),
    })
    messages = messages[-50:]      # limit to 50 right away
    save_messages(messages)

    #handle multiple triggers
    handle_triggers(original_content, messages)
    return "OK", 200
def is_off_topic(text):
    #returns True if the text contains any off-topic keywords
    lower_text = text.lower()
    for word in OFF_TOPIC_KEYWORDS:
        if word in lower_text:
            return True
    return False

def handle_triggers(user_input, messages):
    triggers = {
        "hello" : "Hello! Thanks for greeting my football Channel",
        "help" : "List of commands: 'hello', 'help', 'bye', 'ping', 'soccer', 'goat', 'current world champions', 'current EURO champions'. Type one to see what happens!",
        "bye" : "Goodbye! See ya next time.",
        "ping" : "Pong! I'm alive. HAHA!",
        "soccer" : "I think you mean Football!",
        "goat" : "Lionel Messi",
        "current world champions" : "Argentina",
        "current EURO champions" : "Spain"
    }
    lowerc = user_input.lower()
    added_reply = False

    for keyword, reply_text in triggers.items():
        if keyword in lowerc:
            messages.append({
                'content': reply_text,
                'sender': "FootballBot",
                'timestamp': datetime.datetime.now().isoformat(),
                'extra': None
            })
            added_reply = True

    #keep the last 50 messages
    messages = messages[-50:]
    save_messages(messages)


def read_messages():
    global CHANNEL_FILE
    try:
        with open(CHANNEL_FILE, 'r') as f:
            messages = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
         # If no file or invalid JSON, create an empty file with welcome message
         messages = [WELCOME_MESSAGE]

    return messages

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)

# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == '__main__':
    app.run(port=5001, debug=True)
