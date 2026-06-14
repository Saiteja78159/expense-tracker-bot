"""
utils/llm.py
"""
import logging
import httpx
from config.settings import LLAMA_API_KEY, LLAMA_BASE_URL

LLAMA_MODEL = "llama-3.1-8b-instant"

logger = logging.getLogger(__name__)

async def ask_llm(system_prompt: str, user_message: str, expect_json: bool = False) -> str:
    if not LLAMA_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")

    if expect_json:
        system_prompt += "\n\nIMPORTANT: Reply ONLY with valid JSON. No explanation, no markdown."

    url = f"{LLAMA_BASE_URL.rstrip('/')}/chat/completions"

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

    logger.info(f"Calling LLM: url={url}, model={LLAMA_MODEL}, key_prefix={LLAMA_API_KEY[:8]}")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=payload)
        logger.info(f"LLM response status: {resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"LLM error body: {resp.text}")
        resp.raise_for_status()
        result = resp.json()

    text = result["choices"][0]["message"]["content"].strip()

    if expect_json and text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return text