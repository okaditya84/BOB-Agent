"""Lexical RAG retriever over the BoB knowledge base.

The KB is small (~25 KB), so a TF-IDF-weighted lexical retriever is faster and
more transparent than a vector store while giving solid grounding. The interface
(`search`) is deliberately simple so an embedding-based retriever can be swapped
in later without changing callers.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "of", "the", "a", "an", "for", "and", "or", "with", "in", "to", "on", "as",
    "any", "one", "is", "are", "i", "do", "need", "what", "which", "my", "me",
    "can", "how", "open", "documents", "document",
}
_NON_CATEGORY = {"meta", "core_kyc", "source_pages"}


def _tokens(s: str) -> list[str]:
    return [t for t in _TOKEN.findall(s.lower()) if t not in _STOP and len(t) > 1]


def _flatten_strings(value) -> list[str]:
    out: list[str] = []

    def walk(v):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    walk(value)
    return out


@dataclass
class Chunk:
    product_id: str | None
    title: str
    text: str
    tokens: set[str] = field(default_factory=set)
    title_tokens: set[str] = field(default_factory=set)


@dataclass
class Hit:
    product_id: str | None
    title: str
    text: str
    score: float


def _make_chunk(product_id, title, text) -> Chunk:
    return Chunk(
        product_id=product_id, title=title, text=text,
        tokens=set(_tokens(text)), title_tokens=set(_tokens(title)),
    )


class LexicalRetriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        df: dict[str, int] = {}
        for c in chunks:
            for t in c.tokens:
                df[t] = df.get(t, 0) + 1
        n = len(chunks) or 1
        self.idf = {t: math.log(1 + n / (1 + d)) for t, d in df.items()}

    @classmethod
    def from_kb(cls, path: str | Path) -> "LexicalRetriever":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(cls._build_chunks(raw))

    @staticmethod
    def _build_chunks(raw: dict) -> list[Chunk]:
        chunks: list[Chunk] = []
        core = raw.get("core_kyc", {})
        chunks.append(
            _make_chunk(
                None, "Core KYC documents",
                "Core KYC documents required for almost every account, deposit and loan: "
                + "; ".join(_flatten_strings(core)),
            )
        )
        for key, val in raw.items():
            if key in _NON_CATEGORY or not isinstance(val, dict):
                continue
            label = val.get("category_label", key.replace("_", " "))
            if "sub_types" in val and isinstance(val["sub_types"], list):
                common = _flatten_strings(val.get("common_documents", []))
                for st in val["sub_types"]:
                    if not isinstance(st, dict):
                        continue
                    docs = _flatten_strings({k: v for k, v in st.items()
                                             if k not in ("id", "name", "description")})
                    title = st.get("name", st.get("id", ""))
                    text = (f"{title} — {label}. {st.get('description', '')} "
                            f"Documents: " + "; ".join(common + docs))
                    chunks.append(_make_chunk(st.get("id"), title, text))
            else:
                for child_key, child in val.items():
                    if not isinstance(child, dict):
                        continue
                    docs = _flatten_strings({k: v for k, v in child.items()
                                             if k != "category_label"})
                    if not docs:
                        continue
                    title = child.get("category_label", child_key.replace("_", " "))
                    text = f"{title} — {label}. Documents: " + "; ".join(docs)
                    chunks.append(_make_chunk(child_key, title, text))
        return chunks

    def search(self, query: str, k: int = 5) -> list[Hit]:
        q = set(_tokens(query))
        if not q:
            return []
        scored: list[tuple[float, Chunk]] = []
        for c in self.chunks:
            overlap = q & c.tokens
            if not overlap:
                continue
            score = sum(self.idf.get(t, 0.0) for t in overlap) / math.sqrt(len(c.tokens) + 1)
            score += 0.6 * len(q & c.title_tokens)  # boost product-name matches
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [Hit(c.product_id, c.title, c.text, round(s, 4)) for s, c in scored[:k]]
