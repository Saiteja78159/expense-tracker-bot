# """
# utils/llm.py — Thin wrapper around the Llama model (served via Groq).
# Every agent calls `ask_llm()` with a system prompt + user message.
# """

# import json
# import httpx
# from config.settings import LLAMA_API_KEY, LLAMA_MODEL, LLAMA_BASE_URL


# async def ask_llm(system_prompt: str, user_message: str, expect_json: bool = False) -> str:
#     """
#     Sends a chat completion request to the Llama model.

#     Args:
#         system_prompt:  Tells the model what role it plays (parser, classifier…).
#         user_message:   The actual content to process.
#         expect_json:    If True, appends a strict JSON reminder to the system prompt.

#     Returns:
#         The model's text response (stripped).
#     """
#     if expect_json:
#         system_prompt += "\n\nIMPORTANT: Reply ONLY with valid JSON. No explanation, no markdown."

#     headers = {
#         "Authorization": f"Bearer {LLAMA_API_KEY}",
#         "Content-Type": "application/json",
#     }

#     payload = {
#         "model": LLAMA_MODEL,
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user",   "content": user_message},
#         ],
#         "temperature": 0.1,    # Low temperature = deterministic, factual output
#         "max_tokens": 512,
#     }

#     async with httpx.AsyncClient(timeout=15) as client:
#         resp = await client.post(
#             f"{LLAMA_BASE_URL}/chat/completions",
#             headers=headers,
#             json=payload,
#         )
#         resp.raise_for_status()
#         result = resp.json()

#     text = result["choices"][0]["message"]["content"].strip()

#     # Strip accidental markdown fences like ```json ... ```
#     if expect_json and text.startswith("```"):
#         text = text.split("```")[1]
#         if text.startswith("json"):
#             text = text[4:]
#         text = text.strip()

#     return text


"""
utils/llm.py — Thin wrapper around the Llama model (served via Groq).
Every agent calls `ask_llm()` with a system prompt + user message.
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
            {"role": "user",   "content": user_message},
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