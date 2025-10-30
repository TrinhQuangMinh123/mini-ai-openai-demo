import os
import subprocess
import sys
import time

import pytest
import requests


BASE_URL = "http://127.0.0.1:8001"


def wait_for_health(url: str, retries: int = 40, delay: float = 0.5) -> None:
    for _ in range(retries):
        try:
            resp = requests.get(f"{url}/health", timeout=2)
            resp.raise_for_status()
            return
        except requests.RequestException:
            time.sleep(delay)
    raise RuntimeError("Server failed to become healthy.")


@pytest.fixture(scope="session")
def server_process():
    env = os.environ.copy()
    env.setdefault("PORT", "8001")
    env.setdefault("MODEL_CACHE_DIR", "models/tests_tiny_gpt2")
    proc = subprocess.Popen([sys.executable, "scripts/server.py"], env=env)
    try:
        wait_for_health(BASE_URL)
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_chat_completion(server_process):
    models_resp = requests.get(f"{BASE_URL}/v1/models", timeout=10)
    models_resp.raise_for_status()
    models = models_resp.json()["data"]
    assert models, "API did not return any models"

    payload = {
        "model": models[0]["id"],
        "messages": [
            {"role": "system", "content": "You are a short assistant."},
            {"role": "user", "content": "Respond with a single word greeting."},
        ],
        "max_tokens": 8,
        "temperature": 0.0,
        "top_p": 0.9,
    }
    chat_resp = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=30)
    chat_resp.raise_for_status()
    data = chat_resp.json()
    assert data["choices"][0]["message"]["content"].strip(), "Empty completion received"
