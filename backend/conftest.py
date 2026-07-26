"""pytest bootstrap — puts the backend/ directory on sys.path.

This makes the absolute imports used across the backend (e.g.
``from models.requests import BuildRequest``) resolvable whether pytest is
invoked as ``python -m pytest`` (CWD already on path) or plain ``pytest``
(which only adds the test file's own directory).
"""
import os
import sys

_BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
