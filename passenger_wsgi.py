import os
import sys

# Insert the project directory into sys.path
sys.path.insert(0, os.path.dirname(__file__))

from bot import app as application