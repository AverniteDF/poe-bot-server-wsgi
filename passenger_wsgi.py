import importlib.util
import os
import sys

# Insert the project directory into sys.path
sys.path.insert(0, os.path.dirname(__file__))

# Define the path to your main application file
app_path = os.path.join(os.path.dirname(__file__), 'bot.py')

# Use importlib to load the bot module
spec = importlib.util.spec_from_file_location("bot", app_path)
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

# Define the WSGI application
application = bot.app