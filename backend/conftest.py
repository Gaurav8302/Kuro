import os
import sys

# Ensure the backend folder itself is on sys.path so imports like `routing.*` and `chatbot` work in tests
BACKEND_DIR = os.path.dirname(__file__)
sys.path.insert(0, BACKEND_DIR)
