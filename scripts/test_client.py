#!/usr/bin/env python
"""Utility script that validates the local OpenAI-compatible API."""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Iterable

import requests

try:
    from pyngrok import ngrok  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    ngrok = None


def wait_for_server(base_url: str, retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(f"{base_url}/health", timeout=2)
            resp.raise_for_status()
            return
        except requests.RequestException as exc:
            print(f"[wait] attempt {attempt}/{retries} failed: {exc}")
            time.sleep(delay)
    raise RuntimeError(f"Server at {base_url} did not become ready.")


def format_messages(pairs: Iterable[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"role": role, "content": content} for role, content in pairs]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--use-ngrok", action="store_true", help="Expose the API through ngrok")
    parser.add_argument("--ngrok-authtoken", help="Override NGROK_AUTHTOKEN env var")
    args = parser.parse_args(argv)

    base_url = f"http://{args.host}:{args.port}"
    tunnel_url = None

    if args.use_ngrok:
        if ngrok is None:
            raise SystemExit("pyngrok is not installed. Install and retry.")
        authtoken = args.ngrok_authtoken or os.getenv("NGROK_AUTHTOKEN")
        if not authtoken:
            raise SystemExit("Set NGROK_AUTHTOKEN or pass --ngrok-authtoken when using --use-ngrok.")
        ngrok.set_auth_token(authtoken)
        tunnel = ngrok.connect(args.port, "http")
        tunnel_url = tunnel.public_url
        base_url = tunnel_url
        print(f"[ngrok] Public URL: {tunnel_url}")

    wait_for_server(base_url.rstrip("/v1"))

    models_resp = requests.get(f"{base_url}/v1/models", timeout=10)
    models_resp.raise_for_status()
    models = models_resp.json().get("data", [])
    if not models:
        raise SystemExit("No models reported by the API.")
    model_id = models[0]["id"]
    print(f"[info] Using model: {model_id}")

    client_messages = format_messages(
        [
            ("system", "You are a helpful assistant."),
            ("user", "Say hello in 5 words."),
        ]
    )

    payload = {
        "model": model_id,
        "messages": client_messages,
        "max_tokens": 60,
        "temperature": 0.7,
        "top_p": 0.8,
    }
    chat_resp = requests.post(f"{base_url}/v1/chat/completions", json=payload, timeout=30)
    chat_resp.raise_for_status()
    choice = chat_resp.json()["choices"][0]["message"]
    print(f"[chat] {choice['content']}\n")

    security_messages = format_messages(
        [
            ("system", "You analyze payloads for penetration testing scenarios."),
            (
                "user",
                (
                    "Original payload: cat${IFS}/etc/passwd\n"
                    "CVE: CVE-1999-1556\n"
                    "Return three obfuscated variants in a JSON array."
                ),
            ),
        ]
    )
    payload.update({"messages": security_messages, "temperature": 0.2, "top_p": 0.7})
    sec_resp = requests.post(f"{base_url}/v1/chat/completions", json=payload, timeout=30)
    sec_resp.raise_for_status()
    print(f"[sec] {sec_resp.json()['choices'][0]['message']['content']}")

    if tunnel_url:
        print(f"[done] Tunnel remains active at {tunnel_url}. Ctrl+C to close.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
