# """
# Shared LangChain LLM wrapper — replaces the old raw Groq client.
# Both the classifier and generator import get_llm() from here.

# If GROQ_API_KEY isn't set, MOCK_MODE is on and callers fall back to
# their own heuristic/template logic (see classifier & generator files).
# """
# import os
# from dotenv import load_dotenv
# from langchain_groq import ChatGroq

# load_dotenv()  # reads .env in the project root into os.environ, if present

# GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# MOCK_MODE = GROQ_API_KEY is None

# _llm = None


# def get_llm(temperature: float = 0):
#     global _llm
#     if MOCK_MODE:
#         raise RuntimeError(
#             "GROQ_API_KEY not set - get_llm() needs a real key. "
#             "Callers should use their mock-mode fallback instead."
#         )
#     if _llm is None:
#         _llm = ChatGroq(
#             model="llama-3.3-70b-versatile",
#             temperature=temperature,
#             api_key=GROQ_API_KEY,
#         )
#     return _llm



"""
Shared LangChain LLM wrapper — replaces the old raw Groq client.
Both the classifier and generator import get_llm() from here.

If GROQ_API_KEY isn't set, MOCK_MODE is on and callers fall back to
their own heuristic/template logic (see classifier & generator files).

FIX (2026-08-20), part 2 — the REAL root cause:
llama-3.3-70b-versatile has been deprecated and removed from Groq
entirely. Every call was failing with a 404 model_not_found error
(confirmed via /logs), before JSON parsing was ever reached. The
earlier response_format fix was solving a real but secondary issue —
this was the actual blocker. Switched to openai/gpt-oss-120b, Groq's
current recommended general-purpose model, which also supports
response_format={"type": "json_object"} for structured output.
"""
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()  # reads .env in the project root into os.environ, if present

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MOCK_MODE = GROQ_API_KEY is None

# llama-3.3-70b-versatile is deprecated/removed on Groq — do not revert to it.
# See: https://console.groq.com/docs/deprecations
GROQ_MODEL = "openai/gpt-oss-120b"

_llm = None


def get_llm(temperature: float = 0, json_mode: bool = True):
    """
    json_mode=True (default) enables Groq's JSON response format, which
    both the classifier and generator rely on since they parse the
    output with JsonOutputParser. Pass json_mode=False only if you add
    a caller that expects free-text output.
    """
    global _llm
    if MOCK_MODE:
        raise RuntimeError(
            "GROQ_API_KEY not set - get_llm() needs a real key. "
            "Callers should use their mock-mode fallback instead."
        )

    model_kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}

    # Don't reuse a cached client if json_mode differs from what it was
    # built with — cheap to rebuild, avoids subtle bugs if this ever
    # gets called with mixed settings.
    if _llm is None or getattr(_llm, "_built_json_mode", None) != json_mode:
        _llm = ChatGroq(
            model=GROQ_MODEL,
            temperature=temperature,
            api_key=GROQ_API_KEY,
            model_kwargs=model_kwargs,
        )
        _llm._built_json_mode = json_mode
    return _llm


if __name__ == "__main__":
    # Quick sanity check: confirms the model name is actually live on
    # your account before you go debug the rest of the pipeline again.
    if MOCK_MODE:
        print("MOCK_MODE is on (no GROQ_API_KEY) — nothing to test.")
    else:
        llm = get_llm()
        resp = llm.invoke('Respond with JSON: {"ok": true}')
        print("Model responded OK:", resp.content)