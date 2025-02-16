## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests
from better_profanity import profanity #for filtering

#load the defult list of th bad words
profanity.load_censor_words()

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!' # change to something random, no matter what

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "Sajjad's Channel"
CHANNEL_ENDPOINT = "http://localhost:5001" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

#simple welcome message to insert if the file is empty
WELCOME_MESSAGE = {
    'content' : "Welcome to all!",
    'sender' : "System",
    'timestamp' : "2025-02-16T00:00:00",
    'extra' : None
}

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
    
    #FILTER unwanted content or profanity
    original_content = message['content']
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
    #limit to the last 50 messages
    messages = messages[-50:]

    save_messages(messages)

    if "hello" in original_content.lower():
        auto_reply(messages, "Hello! Thanks for greeting Sajjad’s Channel.")

    return "OK", 200

def auto_reply(messages, reply_text):
    """
    A simple function that appends an automatic response to the message list.
    """
    import datetime
    messages.append({
        'content': reply_text,
        'sender': "Sajjad’s Channel Bot",
        'timestamp': datetime.datetime.now().isoformat(),
        'extra': None
    })
    # Again limit to last 50
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
