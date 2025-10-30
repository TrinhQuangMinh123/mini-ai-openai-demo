# Local OpenAI-Compatible Demo

This mini repository turns the original Kaggle-only vLLM notebook into a lightweight project that can be launched on a CPU-only machine. It keeps the core ideas from the prototype—start a local OpenAI-style API, expose it through ngrok, and exercise the endpoint from a client or test suite—while removing Kaggle-specific setup.

## Project Layout
- `scripts/server.py` – Flask server that wraps a tiny Hugging Face model behind OpenAI-compatible `/v1/models` and `/v1/chat/completions` endpoints.
- `scripts/test_client.py` – Simple client script that sends a request to the local API (or an ngrok-exposed URL).
- `notebooks/local-openai-demo.ipynb` – Updated walk-through notebook for running the full workflow locally.
- `tests/test_api.py` – Pytest that exercises the chat completion endpoint.
- `requirements.txt` – Python dependencies. Install into a virtualenv with `python -m venv .venv && source .venv/bin/activate` before `pip install -r requirements.txt`.

## Quickstart
1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Download the demo model (first run only)**  
   The server pulls `sshleifer/tiny-gpt2` through the Hugging Face Hub. If you need auth, export `HF_TOKEN` before launching.
3. **Start the API server**
   ```bash
   python scripts/server.py
   ```
   Default host/port: `0.0.0.0:8000`.
4. **Expose through ngrok (optional)**
   ```bash
   export NGROK_AUTHTOKEN=your_token
   python scripts/test_client.py --use-ngrok
   ```
   The script opens a tunnel, prints the public URL, and sends a sample chat request.
5. **Run automated test**
   ```bash
   pytest
   ```

## Environment Variables
- `MODEL_REPO` – Override the default Hugging Face repo (`sshleifer/tiny-gpt2`).
- `MODEL_CACHE_DIR` – Directory that stores downloaded weights (default `models/<repo>`).
- `HF_TOKEN` – Hugging Face access token if the repo is gated.
- `NGROK_AUTHTOKEN` – Required when creating a tunnel.

## Notes
- The chosen model is intentionally tiny so the demo runs on CPU-only machines. Swap `MODEL_REPO` for something larger once you have GPU resources.
- All secrets that were in the Kaggle notebook are now read from env vars; nothing sensitive is stored in code.
- The notebook mirrors the shell scripts so you can follow the workflow interactively.
