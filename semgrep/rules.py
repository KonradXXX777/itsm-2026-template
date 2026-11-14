# ai-generated: 100% - Codex constructed positive and negative Semgrep fixtures.
import os
import sqlite3


def kb_defaults():
    # ruleid: plaintext-kb-default
    local = os.getenv("KB_INDEX_URL", "http://kb-index:8080")
    # ok: plaintext-kb-default
    tls = os.getenv("KB_INDEX_URL", "https://kb.internal")
    # ok: plaintext-kb-default
    required = os.getenv("KB_INDEX_URL")
    # ok: plaintext-kb-default
    other = os.getenv("STATUS_URL", "http://status:8080")
    return local, tls, required, other


def databases(path):
    # ruleid: persistent-sqlite-open
    persistent = sqlite3.connect(path, timeout=10)
    # ok: persistent-sqlite-open
    ephemeral = sqlite3.connect(":memory:")
    return persistent, ephemeral
