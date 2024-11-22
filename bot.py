# bot.py

"""
WSGI (Synchronous) Bot Server for Poe Platform
----------------------------------------------
This is a partially-implemented bot server that interacts with the Poe platform.
It is currently capable of echoing messages back to the Poe client/user.
The ultimate goal, however, is for it to be able to forward user messages to other bots on Poe and then relay the responses back to the user.
The challenge is for all of this to be done in a purely synchronous fashion (no async).
This means that asynchronous libraries such as `fastapi` and `fastapi_poe` cannot be used.
The good news is that, at a basic level, interacting with the Poe platform is done via HTTP requests and responses containing JSON.
It's just formatted data being passed back and forth so we can do it with a custom implementation (once we know what the expected format is).
If this goal is achieved then it will be possible to create bot servers using WSGI Python web applications, which are easy to set up in cPanel and don't require cloud service.
These server bots won't handle heavy usage well but should work fine for personal use, experimentation, and light traffic scenarios.

A functioning instance of this bot is available on Poe as 'Server-Bot-WSGI' (by @robhewitt).
The source for this project can be downloaded from GitHub (https://github.com/AverniteDF/poe-bot-server-wsgi).
Contributors are welcome to help advance this bot, particularly if they have insights into the Poe API's JSON payloads for bot-to-bot communication.
"""

import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort, Response, jsonify
import requests # (Questions: Is `requests` sufficient or should we use `httpx` instead? | Should we use HTTP/1.1 or HTTP/2 to communicate with Poe?)
import json
import time
import random

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()
ACCESS_KEY = os.getenv('ACCESS_KEY')
BOT_NAME = os.getenv('BOT_NAME')

if not ACCESS_KEY:
    raise ValueError("ACCESS_KEY environment variable not set")

if not BOT_NAME:
    raise ValueError("BOT_NAME environment variable not set")

# Configure logging
stdout_log_path = os.path.join(os.path.dirname(__file__), 'stdout.log')
stderr_log_path = os.path.join(os.path.dirname(__file__), 'stderr.log')

# Create handlers
stdout_handler = logging.FileHandler(stdout_log_path)
stdout_handler.setLevel(logging.INFO)
stdout_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
stdout_handler.setFormatter(stdout_formatter)

stderr_handler = logging.FileHandler(stderr_log_path)
stderr_handler.setLevel(logging.ERROR)
stderr_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
stderr_handler.setFormatter(stderr_formatter)

# Get the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set to the lowest level you want to capture

# Remove default handlers to avoid duplication
if logger.hasHandlers():
    logger.handlers.clear()

# Add custom handlers
logger.addHandler(stdout_handler)
logger.addHandler(stderr_handler)

# Bot Settings
# Whenever these are changed you must manually prompt Poe's server to make a settings request by running the command: curl -X POST https://api.poe.com/bot/fetch_settings/<BOT_NAME>/<ACCESS_KEY>
INTRO_MESSAGE = 'Hello! Be advised that this bot is under development.'
THIRD_PARTY_BOT = 'GPT-4o-Mini' # Declare which remote bot we will be relaying messages to and from (Question: Will the remote bot stream its response to this bot or send it all at once?)

def mask_access_key(key):
    """
    Masks the ACCESS_KEY by showing the first two and last two characters,
    replacing the intermediate characters with asterisks.
    """
    if not key or len(key) < 16:
        # If the key is too short or empty, mask the entire key
        return '*' * len(key)
    return f"{key[:2]}{'*' * (len(key) - 4)}{key[-2:]}"

def send_event(event_type, data):
    """
    Formats an event in SSE format.
    """
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

class Conversation:
    """
    A class to encapsulate the conversation list and provide methods to access messages.
    """
    def __init__(self, query_list):
        self.query_list = query_list

    def get_messages(self, role=None, order=None):
        """
        Retrieves messages based on role and order.

        :param role: 'user', 'system', 'bot', or None for all roles.
        :param order: 'first', 'last', or None for all messages.
        :return: A single message string or a list of messages.
        """
        if role:
            filtered = [msg['content'] for msg in self.query_list if msg.get('role') == role]
        else:
            filtered = [msg['content'] for msg in self.query_list]

        if order == 'first':
            return filtered[0] if filtered else ""
        elif order == 'last':
            return filtered[-1] if filtered else ""
        else:
            return filtered

    def sender(self):
        """
        Retrieves the role of the sender of the last message in the conversation.

        :return: A string representing the role ('user', 'bot', 'system', etc.)
                 Returns 'unknown' if the conversation is empty or role is missing.
        """
        if not self.query_list:
            return 'unknown'

        last_message = self.query_list[-1]
        return last_message.get('role', 'unknown')

def forward_to_third_party_bot(conversation):
    """
    Forwards the conversation to the third-party bot and returns its response.

    :param conversation: The Conversation object containing previous messages.
    :return: A response object from the third-party bot.
    """
    try:
        # Define the third-party bot's URL (Question: Is the URL below correct? Can someone confirm?)
        third_party_bot_url = f"https://api.poe.com/bot/{THIRD_PARTY_BOT}"

        # Construct the payload based on the incoming query (Question: Is this payload structure correct and complete?)
        payload = {
            "version": "1.1",
            "type": "query",
            "query": conversation.query_list,  # Forward the entire query list
            "language_code": "en"  # Optional: Adjust based on your use case
        }

        # Set the headers, including the Authorization header for the third-party bot
        # Question: Do we need to specify whether the response should be streamed or not by adding an "Accept" header? (i.e., "Accept": "text/event-stream" OR "Accept": "application/json")
        # It only makes sense to get a streaming responses if we relay that stream back to the Poe client as we receive it. Getting it all at once will be simpler as long as there aren't any timeout issues. Reminder: The Poe client requires an initial response within 5 seconds
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ACCESS_KEY}" # Use the same ACCESS_KEY
        }

        # Make the POST request (NOTE: If response is being streamed we will need to add code to handle that)
        logger.info(f"Forwarding conversation to third-party bot '{THIRD_PARTY_BOT}' at {third_party_bot_url}.")
        response = requests.post(third_party_bot_url, json=payload, headers=headers, timeout=10)

        # Check if the response was successful (Currently, a RequestException is being thrown: "Response ended prematurely")
        if response.status_code == 200:
            logger.info(f"Received response from third-party bot '{THIRD_PARTY_BOT}'.")
            return response.json()
        else:
            logger.error(f"Error from third-party bot '{THIRD_PARTY_BOT}': {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception while communicating with third-party bot '{THIRD_PARTY_BOT}': {e}")
        return None

def get_random_message():
    # Return a random line from the 'messages.txt' file
    try:
        with open('messages.txt', 'r') as file:
            lines = file.readlines()
            if lines:
                return random.choice(lines).strip()
            else:
                return "No additional messages available."
    except FileNotFoundError:
        return "Error: messages.txt file not found."

def compose_echo_reply(conversation):
    # Echo back the user's messages in ALL CAPS
    user_messages_uppercase = [message.upper() for message in conversation.get_messages('user')]
    return '\n'.join(user_messages_uppercase)

def generate_streaming_response_to_user(text):
    """
    We are replying to user so generate a stream of SSEs to define the message (contribution to conversation) we are sending back.
    """
    try:
        # Send 'meta' event
        meta = {
            "content_type": "text/markdown",
            "suggested_replies": False
        }
        yield send_event("meta", meta)
        logger.info("Bot: Sent 'meta' event.")
        time.sleep(0.1)  # Simulate processing delay

        text_event = {
            "text": text
        }
        yield send_event("text", text_event)
        logger.info("Bot: Sent 'text' event.")
        time.sleep(0.1)  # Simulate processing delay

        # Send 'done' event to indicate the end of the response
        done_event = {}
        yield send_event("done", done_event)
        logger.info("Bot: Sent 'done' event.")
    except Exception as e:
        # In case of any unexpected error, send an 'error' event
        error_event = {
            "allow_retry": False,
            "text": "An internal error occurred.",
            "error_type": "internal_error"
        }
        yield send_event("error", error_event)
        logger.error(f"Bot: Sent 'error' event due to exception: {e}")
        yield send_event("done", {})
        logger.info("Bot: Sent 'done' event after error.")

def on_conversation_update(conversation):
    """
    A conversation update was received. The most recent message in the conversation is expected to be from 'user'.
    This (local) bot must either stream a response to the user or forward the conversation to a remote bot and wait for a response.
    If the conversation update came from a user then an initial response (streamed event) must be given within 5 seconds (a rule imposed by Poe).
    Note that bot dependencies must be declared (via response to `settings` request) in order for remote bots to participate.
    """
    sender = conversation.sender()

    if sender == 'user':
        attempt_relay = False # For testing purposes we can enable or disable
        if THIRD_PARTY_BOT and attempt_relay:
            logger.info(f"Received conversation update from user. Forwarding to '{THIRD_PARTY_BOT}'.")

            # Relay the conversation to the third-party bot
            third_party_response = forward_to_third_party_bot(conversation)

            if third_party_response:
                # Extract the text content from the third-party bot's response
                reply_text = third_party_response.get("content", "No response from third-party bot.")
                return Response(generate_streaming_response_to_user(reply_text), mimetype='text/event-stream')
            else:
                # If the third-party bot fails, send an error event
                error_event = {
                    "allow_retry": False,
                    "text": "Failed to retrieve a response from the third-party bot.",
                    "error_type": "third_party_error"
                }
                return Response(
                    send_event("error", error_event) + send_event("done", {}),
                    status=200,
                    mimetype='text/event-stream'
                )
        else: # No third-party bot specified or relaying disabled; echo back the user's message
            return Response(generate_streaming_response_to_user(compose_echo_reply(conversation) + '\n\n---\n\n' + get_random_message()), mimetype='text/event-stream')
    else:
        logger.error(f"Unexpected sender role: {sender}.")
        abort(400, description="Unexpected sender role.")

@app.before_request
def log_request_info():
    """
    Logs information about each incoming request before it's processed.
    Masks the ACCESS_KEY in the Authorization header to enhance security.
    """
    logger.info(f"Received {request.method} request on {request.path}")

    # Create a copy of headers to avoid modifying the original request headers
    headers = dict(request.headers)

    # Check if the Authorization header is present and mask the ACCESS_KEY
    if 'Authorization' in headers:
        auth = headers['Authorization']
        # Assuming the format is "Bearer <ACCESS_KEY>"
        parts = auth.split(' ')
        if len(parts) == 2:
            auth_type, access_key = parts
            masked_key = mask_access_key(access_key)
            headers['Authorization'] = f"{auth_type} {masked_key}"
        else:
            # If the format is unexpected, mask the entire Authorization header
            headers['Authorization'] = mask_access_key(auth)

    logger.info(f"Headers: {headers}")

    if request.method == 'POST':
        try:
            payload = request.get_json()
            logger.info(f"JSON Payload: {json.dumps(payload)}")
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")

@app.route('/', methods=['GET', 'POST'])
def handle_http_request():
    """
    Handles both GET and POST requests at the root endpoint.

    GET is used to verify deployment and environment variables.
    Displays the BOT names and a masked version of ACCESS_KEY.
    """
    if request.method == 'GET':
        # Handle GET request (assume URL was browser-accessed for testing purposes)
        masked_access_key = mask_access_key(ACCESS_KEY)
        return f"""
        Hello from {BOT_NAME}!<br>
        ACCESS_KEY: {masked_access_key}<br><br>
        Python web application is up and running.
        """, 200

    elif request.method == 'POST':
        # Handle POST request (the Content-Type is expected to be 'application/json')
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' not in content_type.lower():
            logger.error(f"Unrecognized Content-Type: {content_type}")
            abort(415, description="Unrecognized/unhandled content type.")

        auth_header = request.headers.get('Authorization')
        expected_auth = f"Bearer {ACCESS_KEY}"

        if auth_header != expected_auth:
            logger.warning("Unauthorized access attempt.")
            abort(403, description="Not authenticated")

        try:
            data = request.get_json()
            if not data:
                logger.warning("Invalid request format: no JSON data.")
                abort(400, description="Invalid request format")
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            abort(400, description="Invalid JSON format")

        request_type = data.get('type')

        if request_type == 'settings':
            logger.info("Received 'settings' type request.")

            response = {
                "server_bot_dependencies" : {THIRD_PARTY_BOT: 1}, # Declare third-party bots (here we pre-authorize 1 call to the THIRD_PARTY_BOT)
                "introduction_message" : INTRO_MESSAGE
            }
            logger.info(f"Responding to settings request: {response}")
            return jsonify(response), 200

        elif request_type == 'query':
            logger.info("Received 'query' type request.")

            # Extract the entire query list
            try:
                query_list = data.get('query', [])
                if not query_list:
                    raise ValueError("Query list is empty.")
                logger.info(f"Received query list with {len(query_list)} messages.")
                conversation = Conversation(query_list)
            except (TypeError, ValueError) as e:
                logger.error(f"Error extracting query list: {e}")
                # Send an 'error' event
                error_event = {
                    "allow_retry": False,
                    "text": "Invalid query format: unable to extract query list.",
                    "error_type": "invalid_query_format"
                }
                return Response(
                    send_event("error", error_event) + send_event("done", {}),
                    status=200,
                    mimetype='text/event-stream'
                )

            return on_conversation_update(conversation)

        else:
            logger.warning("Invalid request format: unrecognized 'type'.")
            abort(400, description="Invalid request format")

if __name__ == '__main__':
    app.run(debug=False)