"""Tiny zero-dependency .env loader.

Reads KEY=VALUE lines from a .env file into os.environ. Values already present
in the real environment are NOT overwritten (os.environ wins), so deployment
platforms that inject env vars keep working. Supports `#` comments, blank
lines, and optional single/double quotes around values.
"""
import os


def load_env_file(path, environ=None):
    """Load `path` into `environ` (default os.environ). Returns the number of
    keys set. Missing file is fine — returns 0."""
    env = environ if environ is not None else os.environ
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.readlines()
    except OSError:
        return 0
    count = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key and key not in env:
            env[key] = value
            count += 1
    return count
