"""
Root application entrypoint for Gunicorn and Render deployments.
Exposes the Flask 'app' instance from web/server.py.
"""
import os
import sys

# Ensure repository root is in Python sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from web.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
