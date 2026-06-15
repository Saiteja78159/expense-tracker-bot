"""
utils/llm.py — Groq LLM wrapper
"""
import logging
import httpx
from config.settings import LLAMA_API_KEY, LLAMA_BASE_URL

logger = logging.getLogger(__name__)

# Hardcoded model to avoid Railway env variable issues
LLAMA_MODEL = "llama-3.1-8b-instant"


async def ask_llm(system_prompt: str, user_message: str, expect_json: bool = False) -> str:
    if not LLAMA_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in Railway environment variables.")

    if expect_json:
        system_prompt += "\n\nCRITICAL: Reply ONLY with valid JSON. No explanation, no markdown, no backticks."

    url = f"{LLAMA_BASE_URL.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {LLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    logger.info(f"LLM call → model={LLAMA_MODEL}, key={LLAMA_API_KEY[:8]}...")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            logger.error(f"LLM error {resp.status_code}: {resp.text[:300]}")

        if resp.status_code == 401:
            raise ValueError("Invalid GROQ_API_KEY — check Railway Variables.")
        if resp.status_code == 404:
            raise ValueError(
                f"Groq 404: model '{LLAMA_MODEL}' not found or API key missing. "
                f"Key prefix: '{LLAMA_API_KEY[:8]}'"
            )
        if resp.status_code == 429:
            raise ValueError("Groq rate limit hit. Please wait a moment.")

        resp.raise_for_status()
        result = resp.json()

    text = result["choices"][0]["message"]["content"].strip()

    # Clean JSON response if needed
    if expect_json:
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        # Remove any trailing text after closing brace
        if "{" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            text = text[start:end]

    return text
