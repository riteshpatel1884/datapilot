"""
Offline embeddings for the RAG layer.

Schema descriptions and few-shot examples are short, domain-specific
text — a real transformer embedding model is overkill for a v1 demo
and requires downloading weights (needs network + HF access).

This is a simple deterministic hashing-vectorizer that implements
LangChain's Embeddings interface, so the whole RAG pipeline runs
fully offline. Swap in HuggingFaceEmbeddings or OpenAIEmbeddings
later without touching any other file — see bottom of this file.
"""
import hashlib
import math
import re
from langchain_core.embeddings import Embeddings

VECTOR_SIZE = 256


def _tokenize(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


def _hash_token(token: str, dim: int) -> int:
    h = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(h, 16) % dim


class SimpleHashEmbeddings(Embeddings):
    """Deterministic bag-of-words hashing embedding. No downloads, no API calls."""

    def __init__(self, dim: int = VECTOR_SIZE):
        self.dim = dim

    def _embed_text(self, text: str) -> list:
        vec = [0.0] * self.dim
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for token in tokens:
            idx = _hash_token(token, self.dim)
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list) -> list:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> list:
        return self._embed_text(text)


# --- To use a real embedding model instead (needs network access) ---
# from langchain_huggingface import HuggingFaceEmbeddings
# def get_embeddings():
#     return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
#
# For now:
def get_embeddings():
    return SimpleHashEmbeddings()


if __name__ == "__main__":
    emb = SimpleHashEmbeddings()
    v1 = emb.embed_query("who is the best customer by revenue")
    v2 = emb.embed_query("top customer ranked by total revenue")
    v3 = emb.embed_query("list all products in inventory")

    def cosine(a, b):
        return sum(x * y for x, y in zip(a, b))

    print("similar queries similarity:", cosine(v1, v2))
    print("dissimilar queries similarity:", cosine(v1, v3))