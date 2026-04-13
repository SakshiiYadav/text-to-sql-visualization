import requests
import streamlit as st


GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_MODEL = st.secrets.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_llm(prompt: str) -> str:
    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are a precise assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]