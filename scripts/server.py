#!/usr/bin/env python
"""Minimal OpenAI-compatible chat server that runs on CPU."""

from __future__ import annotations

import os
import signal
import sys
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer


def build_prompt(messages: list[dict[str, str]]) -> str:
    """Turn OpenAI-style messages into a simple chat prompt."""
    transcript = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        transcript.append(f"{role}: {content}")
    transcript.append("assistant:")
    return "\n".join(transcript)


def ensure_model(model_repo: str, target_dir: Path) -> Path:
    """Download the model into target_dir if it is not present."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if any(target_dir.iterdir()):
        return target_dir

    hf_token = os.getenv("HF_TOKEN")
    print(f"Downloading {model_repo} to {target_dir}...", flush=True)
    snapshot_download(
        repo_id=model_repo,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        token=hf_token,
    )
    return target_dir


def create_app() -> Flask:
    model_repo = os.getenv("MODEL_REPO", "sshleifer/tiny-gpt2")
    default_cache = Path("models") / model_repo.replace("/", "_")
    model_cache_dir = Path(os.getenv("MODEL_CACHE_DIR", default_cache))
    ensure_model(model_repo, model_cache_dir)

    print("Loading model...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_cache_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_cache_dir)
    model.to("cpu")
    model.eval()
    print("Model ready.", flush=True)

    app = Flask(__name__)
    CORS(app)

    @app.get("/health")
    def healthcheck():
        return {"status": "ok", "model_repo": model_repo}

    @app.get("/v1/models")
    def list_models():
        return jsonify(
            {
                "object": "list",
                "data": [
                    {
                        "id": model_repo,
                        "object": "model",
                        "owned_by": "local",
                    }
                ],
            }
        )

    @app.post("/v1/chat/completions")
    def chat_completions():
        payload = request.get_json(force=True)
        messages = payload.get("messages", [])
        max_tokens = max(16, int(payload.get("max_tokens", 128)))
        temperature = float(payload.get("temperature", 0.7))
        top_p = float(payload.get("top_p", 0.8))

        prompt = build_prompt(messages)
        inputs = tokenizer(prompt, return_tensors="pt")
        output = model.generate(
            **inputs,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=temperature > 0,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=max_tokens,
        )

        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        completion = decoded[len(prompt) :].strip() or decoded

        response_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        finish_reason = "stop"
        usage = {
            "prompt_tokens": len(inputs["input_ids"][0]),
            "completion_tokens": max(0, len(output[0]) - len(inputs["input_ids"][0])),
            "total_tokens": len(output[0]),
        }

        response = {
            "id": response_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_repo,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": completion},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": usage,
        }
        return jsonify(response)

    return app


def main() -> int:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    app = create_app()

    def shutdown_handler(signum, _frame):
        print(f"Received signal {signum}, shutting down...", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    app.run(host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
