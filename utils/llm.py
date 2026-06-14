"""
utils/llm.py
"""
import logging
import httpx
from config.settings import LLAMA_API_KEY, LLAMA_MODEL

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

async def ask_llm(system_prompt: str, user_message: str, expect_json: bool = False) -> str:
    if not LLAMA_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Please add it to your Railway environment variables.")

    if expect_json:
        system_prompt += "\n\nIMPORTANT: Reply ONLY with valid JSON. No explanation, no markdown."

    headers = {
        "Authorization": f"Bearer {LLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(GROQ_URL, headers=headers, json=payload)
        if resp.status_code == 401:
            raise ValueError("Invalid GROQ_API_KEY — check your Railway environment variables.")
        if resp.status_code == 404:
            raise ValueError(
                f"Groq API returned 404. This usually means GROQ_API_KEY is missing or empty. "
                f"Current key prefix: '{LLAMA_API_KEY[:8] if LLAMA_API_KEY else 'EMPTY'}...'"
            )
        resp.raise_for_status()
        result = resp.json()

    text = result["choices"][0]["message"]["content"].strip()

    if expect_json and text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return text
