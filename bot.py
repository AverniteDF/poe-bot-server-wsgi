# bot.py

"""
WSGI (Synchronous) Bot Server for Poe Platform
----------------------------------------------
This is a partially-implemented bot server that interacts with the Poe platform.
It is currently capable of echoing messages back to the Poe client/user.
The ultimate goal is for it to be able to forward user messages to other bots on Poe and relay their responses back to the user.
The challenge is for all of this to be done in a purely synchronous fashion (no async).
This means that asynchronous libraries such as `fastapi` and `fastapi_poe` cannot be used.
At a basic level, interacting with the Poe platform is done via HTTP requests and responses containing JSON.
It's just formatted data being passed back and forth so we can do it with a custom implementation (once we know what the expected format is).
If this goal is achieved then it will be possible to create bot servers using WSGI Python web applications, which are easy to set up in cPanel and don't require cloud service.
These server bots might not handle heavy usage well but should work fine for personal use, experimentation, and light traffic scenarios.

A functioning instance of this bot is available on Poe as 'Server-Bot-WSGI' (by @robhewitt).
The source for this project can be downloaded from GitHub (https://github.com/AverniteDF/poe-bot-server-wsgi).
Contributors are welcome to help advance this bot, particularly if they have insights into the Poe API's JSON payloads for bot-to-bot communication.
"""

import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort, Response, jsonify
import httpx
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
THIRD_PARTY_BOT = 'GPT-4o-Mini'  # Declare which remote bot we will be relaying messages to and from

# Define the third-party bot's API endpoint (Question: Is the URL below correct? Can someone confirm?)
THIRD_PARTY_BOT_API_ENDPOINT = f"https://api.poe.com/bot/{THIRD_PARTY_BOT}"

# Define whether to use HTTP/2
USE_HTTP2 = False

logger.info(f"USE_HTTP2 is set to: {USE_HTTP2}")

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

def log_outgoing_request(request: httpx.Request):
    """
    Logs the actual HTTP request headers and body that is sent to the remote third-party bot.

    :param request: The httpx.Request object being sent.
    """
    logger.info(f"Outgoing HTTP Request to '{request.url}':")
    # Create a copy of headers and mask the ACCESS_KEY so we can log it safely
    headers = mask_access_key_in_headers(request)
    logger.info(f"Headers: {json.dumps(headers, indent=2)}")

    # Log the body
    if request.content:
        try:
            # Attempt to decode as UTF-8 for readable logging
            body = request.content.decode('utf-8')
            logger.info(f"Body: {body}")
        except UnicodeDecodeError:
            # If binary data, log as hexadecimal
            body = request.content.hex()
            logger.info(f"Body (hex): {body}")
    else:
        logger.info("Body: None")

def relay_to_third_party_bot(headers, payload):
    """
    Forwards the request to the third-party bot and streams its response back to the Poe client.

    This function uses the `httpx` library with HTTP/2 enabled to send a POST request to the third-party bot.
    It streams the response as it's received and yields chunks to be relayed to the Poe client.

    :param headers: A copy of the headers from the original request sent from the Poe client.
    :param payload: The payload from the original request sent from the Poe client.
    :return: A generator yielding response chunks from the third-party bot.
    """
    try:
        # Remove 'Content-Length' and 'User-Agent' headers in a case-insensitive manner
        headers = {k: v for k, v in headers.items() if k.lower() not in ['content-length', 'user-agent']}
        headers['Host'] = 'api.poe.com'  # Update the Host header to the third-party API's host

        # Initialize the httpx Client with HTTP/2 enabled based on USE_HTTP2 variable.
        # An event hook is used to log the actual contents of the HTTP POST being sent.
        with httpx.Client(http2=USE_HTTP2, timeout=10.0, event_hooks={'request': [log_outgoing_request]}) as client:
            # Use client.stream() for streaming responses
            with client.stream("POST", THIRD_PARTY_BOT_API_ENDPOINT, headers=headers, json=payload, follow_redirects=True) as response:
                # Raise an exception for bad status codes
                response.raise_for_status()

                logger.info(f"Connected to third-party bot '{THIRD_PARTY_BOT}'. Starting to stream responses.")

                # Iterate over the streamed response
                for chunk in response.iter_text():
                    if chunk:
                        logger.info(f"Received chunk from '{THIRD_PARTY_BOT}': {chunk}")
                        yield chunk  # Yield each chunk to be relayed to the Poe client

        logger.info(f"Finished streaming responses from third-party bot '{THIRD_PARTY_BOT}'.")

    except httpx.RequestError as e:
        logger.error(f"An error occurred while requesting third-party bot '{THIRD_PARTY_BOT}': {e}")
        error_event = {
            "allow_retry": False,
            "text": "Failed to communicate with the third-party bot.",
            "error_type": "third_party_request_error"
        }
        yield send_event("error", error_event)
        yield send_event("done", {})
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from third-party bot '{THIRD_PARTY_BOT}': {e.response.status_code} - {e.response.text}")
        error_event = {
            "allow_retry": False,
            "text": "Third-party bot returned an error.",
            "error_type": "third_party_http_error"
        }
        yield send_event("error", error_event)
        yield send_event("done", {})
    except Exception as e:
        logger.error(f"Unexpected exception in communicating with third-party bot '{THIRD_PARTY_BOT}': {e}")
        error_event = {
            "allow_retry": False,
            "text": "An internal error occurred while communicating with the third-party bot.",
            "error_type": "internal_error"
        }
        yield send_event("error", error_event)
        yield send_event("done", {})

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
    """
    Generator that yields the user's messages in ALL CAPS, one chunk at a time.
    """
    user_messages_uppercase = [message.upper() for message in conversation.get_messages('user')]
    combined_message = '\n'.join(user_messages_uppercase)

    # We'll also tack on a random message to make the reply longer
    combined_message = combined_message + '\n\n---\n\n' + get_random_message()
    
    chunk_size = 10  # Max number of characters to send at a time
    for i in range(0, len(combined_message), chunk_size):
        yield combined_message[i:i+chunk_size]
        time.sleep(0.1)  # Slight delay to simulate streaming

def generate_streaming_response_to_user(text_generator):
    """
    Streams a response to the user by yielding SSEs for each part generated by the text_generator.

    Streaming currently doesn't work as expected because Passenger has a response buffering mechanism.
    It can be effectively disabled by changing Passenger's configuration:
    `passenger_response_buffer_high_watermark = 64`  # Set buffer capacity to a tiny size (64 bytes)
    However, I'm not sure if altering these settings is practical in a shared hosting environment.
    What's needed is a way to disable buffering for a specific response without changing the global setting.

    :param text_generator: A generator function that yields parts of the text to send.
    """
    try:
        # Send 'meta' event
        meta = {
            "content_type": "text/markdown",
            "linkify": True,
            "suggested_replies": False
        }
        yield send_event("meta", meta)
        logger.info("Bot: Sent 'meta' event to Poe client.")
        time.sleep(0.1)  # Simulate processing delay

        # Stream the text piece by piece
        for text_part in text_generator:
            text_event = {
                "text": text_part
            }
            yield send_event("text", text_event)
            logger.info(f"Bot: Sent 'text' event: {text_part.replace('\n', '\\n')}")

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

def on_conversation_update(request):
    """
    A conversation update was received. The most recent message in the conversation is expected to be from 'user'.
    This (local) bot must either stream a response to the user or forward the conversation to a remote bot and wait for a response.
    If the conversation update came from a user then an initial response (streamed event) must be given within 5 seconds (a rule imposed by Poe).
    Note that bot dependencies must be declared (via response to `settings` request) in order for remote bots to participate.
    """
    data = request.get_json()
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

    sender = conversation.sender()

    if sender == 'user':
        attempt_relay = False  # For testing purposes we can enable or disable
        if THIRD_PARTY_BOT and attempt_relay:
            logger.info(f"Received conversation update from user. Forwarding to '{THIRD_PARTY_BOT}'.")

            # Relay the request to the third-party bot and get the generator
            third_party_stream = relay_to_third_party_bot(dict(request.headers), request.get_json())

            # Stream the third-party bot's response back to the Poe client
            return Response(
                generate_streaming_response_to_user(third_party_stream),
                mimetype='text/event-stream'
            )
        else:  # No third-party bot specified or relaying disabled; stream back an echo reply
            headers = { "X-Accel-Buffering": "no" }  # Feeble attempt to disable response buffering (doesn't work)
            return Response(
                generate_streaming_response_to_user(compose_echo_reply(conversation)),
                mimetype='text/event-stream',
                headers=headers
            )
    else:
        logger.error(f"Unexpected sender role: {sender}.")
        abort(400, description="Unexpected sender role.")

def mask_access_key_in_headers(request):
    # Create a copy of headers to avoid modifying the original
    headers = dict(request.headers)

    # Check if the Authorization header is present and mask the ACCESS_KEY in a case-insensitive manner
    for key, value in headers.items():
        if key.lower() == 'authorization':
            auth = value
            # Assuming the format is "Bearer <ACCESS_KEY>"
            parts = auth.split(' ')
            if len(parts) == 2:
                auth_type, access_key = parts
                masked_key = mask_access_key(access_key)
                headers[key] = f"{auth_type} {masked_key}"
            else:
                # If the format is unexpected, mask the entire Authorization header
                headers[key] = mask_access_key(auth)
            break
    return headers

@app.before_request
def log_request_info():
    """
    Logs information about each incoming request before it's processed.
    Masks the ACCESS_KEY in the Authorization header to enhance security.
    """
    logger.info(f"Received {request.method} request on {request.path}")

    # Create a copy of headers and mask the ACCESS_KEY
    headers = mask_access_key_in_headers(request)
    logger.info(f"Headers: {json.dumps(headers, indent=2)}")

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
                "server_bot_dependencies" : {THIRD_PARTY_BOT: 1},  # Declare third-party bots (here we pre-authorize 1 call to the THIRD_PARTY_BOT)
                "introduction_message" : INTRO_MESSAGE
            }
            logger.info(f"Responding to settings request: {response}")
            return jsonify(response), 200

        elif request_type == 'query':
            logger.info("Received 'query' type request.")
            return on_conversation_update(request)

        else:
            logger.warning("Invalid request format: unrecognized 'type'.")
            abort(400, description="Invalid request format")

if __name__ == '__main__':
    app.run(debug=False)