"""
utils/llm.py
"""
import httpx
from config.settings import LLAMA_API_KEY, LLAMA_MODEL

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

async def ask_llm(system_prompt: str, user_message: str, expect_json: bool = False) -> str:
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
        resp.raise_for_status()
        result = resp.json()

    text = result["choices"][0]["message"]["content"].strip()

    if expect_json and text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return text
