"""Small API-key loader for the (optional) two-judge grader.

Grading task outputs calls the Anthropic + OpenAI APIs, which need ANTHROPIC_API_KEY and
OPENAI_API_KEY. If they're already in your environment, nothing else is needed. Otherwise this
loads them from a single file OUTSIDE the repo — so a key can never be committed by accident:

    FILE: ~/.agentic-edge-bench/keys.env   (KEY=VALUE lines; override with AEB_KEYS_FILE)

Keys are loaded into os.environ only for the process that calls ensure_keys() (not exported
globally). The decode/ladder benchmark needs no keys at all — only the grader does.
"""
import os
from pathlib import Path

KEYS_FILE = Path(os.environ.get("AEB_KEYS_FILE", Path.home() / ".agentic-edge-bench" / "keys.env"))

def ensure_keys(required=()):
    """Load the keys file into os.environ (only keys not already set).
    Returns the list of still-missing required keys (empty = all present)."""
    if KEYS_FILE.exists():
        for raw in KEYS_FILE.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k.startswith("export "):
                k = k[len("export "):].strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    return [k for k in required if not os.environ.get(k)]
