from __future__ import annotations
import os
from typing import Optional
from openai import OpenAI

client = None
def _client():
    global client
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client

def generate_answer(prompt: str) -> str:
    cli = _client()
    resp = cli.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are a senior/staff-level software engineer answering concisely."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=400
    )
    return resp.choices[0].message.content.strip()
