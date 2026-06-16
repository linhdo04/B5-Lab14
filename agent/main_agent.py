import asyncio
import json
import math
import os
import re
from collections import Counter
from typing import Dict, List, Tuple


STOPWORDS = {
    "a",
    "ai",
    "an",
    "bo",
    "cac",
    "can",
    "cho",
    "co",
    "cua",
    "de",
    "den",
    "duoc",
    "gi",
    "hay",
    "khi",
    "la",
    "lam",
    "neu",
    "nhung",
    "quy",
    "theo",
    "thi",
    "toi",
    "trong",
    "va",
    "ve",
}


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def cosine_score(query: str, document: str) -> float:
    q_counts = Counter(tokenize(query))
    d_counts = Counter(tokenize(document))
    if not q_counts or not d_counts:
        return 0.0
    numerator = sum(q_counts[token] * d_counts.get(token, 0) for token in q_counts)
    q_norm = math.sqrt(sum(value * value for value in q_counts.values()))
    d_norm = math.sqrt(sum(value * value for value in d_counts.values()))
    return numerator / (q_norm * d_norm)


class MainAgent:
    """
    Small deterministic RAG agent for the lab benchmark.

    The implementation intentionally avoids external API calls so the codelab can be
    reviewed and graded without secrets. It still exposes the same operational
    signals as a real RAG agent: answer, contexts, retrieved document IDs, sources,
    latency, and estimated token usage.
    """

    def __init__(
        self,
        name: str = "SupportAgent-v2",
        corpus_path: str = "data/knowledge_base.json",
        top_k: int = 3,
        threshold: float = 0.12,
        strict_grounding: bool = True,
    ):
        self.name = name
        self.top_k = top_k
        self.threshold = threshold
        self.strict_grounding = strict_grounding
        self.corpus = self._load_corpus(corpus_path)

    def _load_corpus(self, corpus_path: str) -> List[Dict]:
        if not os.path.exists(corpus_path):
            fallback = [
                {
                    "id": "POLICY_PASSWORD_001",
                    "title": "Password reset policy",
                    "source": "it_security_handbook.md",
                    "text": "Nhan vien doi mat khau bang cong thong tin SSO, xac minh MFA, va dat mat khau toi thieu 12 ky tu.",
                }
            ]
            return fallback
        with open(corpus_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def retrieve(self, question: str) -> List[Tuple[Dict, float]]:
        query_tokens = set(tokenize(question))
        scored = []
        for doc in self.corpus:
            document_text = f"{doc['title']} {doc['text']}"
            score = cosine_score(question, document_text)
            title_tokens = set(tokenize(doc["title"]))
            if title_tokens and title_tokens.issubset(query_tokens):
                score += 0.35
            scored.append((doc, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [(doc, score) for doc, score in scored[: self.top_k] if score >= self.threshold]

    def _compose_answer(self, question: str, retrieved: List[Tuple[Dict, float]]) -> str:
        lowered = question.lower()
        if "bo qua" in lowered and ("mat khau" in lowered or "admin" in lowered):
            return (
                "Toi khong the bo qua chinh sach hoac cung cap mat khau. "
                "Theo tai lieu, IT khong bao gio hoi hay chia se mat khau hien tai."
            )

        if not retrieved:
            return "Toi khong co du thong tin trong tai lieu duoc cung cap de tra loi cau hoi nay."

        contexts = [doc["text"] for doc, _ in retrieved]
        if len(contexts) == 1:
            return contexts[0]

        joined = " ".join(contexts)
        if self.strict_grounding:
            return joined
        return contexts[0]

    async def query(self, question: str) -> Dict:
        await asyncio.sleep(0.02)
        retrieved = self.retrieve(question)
        answer = self._compose_answer(question, retrieved)
        contexts = [doc["text"] for doc, _ in retrieved]
        retrieved_ids = [doc["id"] for doc, _ in retrieved]
        sources = [doc["source"] for doc, _ in retrieved]
        token_estimate = len(tokenize(question)) + len(tokenize(answer)) + sum(len(tokenize(ctx)) for ctx in contexts)

        return {
            "answer": answer,
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "agent": self.name,
                "model": "deterministic-rag",
                "tokens_used": token_estimate,
                "sources": sources,
                "retrieval_scores": {doc["id"]: round(score, 4) for doc, score in retrieved},
            },
        }


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Lam the nao de doi mat khau?")
        print(json.dumps(resp, ensure_ascii=False, indent=2))

    asyncio.run(test())
