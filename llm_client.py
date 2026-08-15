"""
Shared LangChain LLM wrapper — replaces the old raw Groq client.
Both the classifier and generator import get_llm() from here.

If GROQ_API_KEY isn't set, MOCK_MODE is on and callers fall back to
their own heuristic/template logic (see classifier & generator files).
"""
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()  # reads .env in the project root into os.environ, if present

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MOCK_MODE = GROQ_API_KEY is None

_llm = None


def get_llm(temperature: float = 0):
    global _llm
    if MOCK_MODE:
        raise RuntimeError(
            "GROQ_API_KEY not set - get_llm() needs a real key. "
            "Callers should use their mock-mode fallback instead."
        )
    if _llm is None:
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            api_key=GROQ_API_KEY,
        )
    return _llm