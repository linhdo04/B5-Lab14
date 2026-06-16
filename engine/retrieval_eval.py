import re
from typing import Dict, List


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


def _jaccard(a: str, b: str) -> float:
    a_tokens = _tokens(a)
    b_tokens = _tokens(b)
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


class RetrievalEvaluator:
    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    def calculate_recall_at_k(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        expected = set(expected_ids)
        retrieved = set(retrieved_ids[:top_k])
        return len(expected & retrieved) / len(expected)

    async def score(self, case: Dict, response: Dict, top_k: int = 3) -> Dict:
        expected_ids = case.get("expected_retrieval_ids", [])
        retrieved_ids = response.get("retrieved_ids", [])
        contexts = " ".join(response.get("contexts", []))
        answer = response.get("answer", "")
        expected_answer = case.get("expected_answer", "")

        retrieval = {
            "hit_rate": self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=top_k),
            "mrr": self.calculate_mrr(expected_ids, retrieved_ids),
            "recall_at_k": self.calculate_recall_at_k(expected_ids, retrieved_ids, top_k=top_k),
            "expected_ids": expected_ids,
            "retrieved_ids": retrieved_ids,
        }

        return {
            "faithfulness": round(_jaccard(answer, contexts), 4) if contexts else (1.0 if "khong co du thong tin" in answer.lower() else 0.0),
            "relevancy": round(max(_jaccard(answer, expected_answer), _jaccard(contexts, expected_answer)), 4),
            "retrieval": retrieval,
        }

    async def evaluate_batch(self, dataset: List[Dict], responses: List[Dict] = None) -> Dict:
        if not responses:
            raise ValueError("responses are required to evaluate retrieval batch metrics")

        hit_rates = []
        mrrs = []
        recalls = []
        for case, response in zip(dataset, responses):
            retrieval = (await self.score(case, response))["retrieval"]
            hit_rates.append(retrieval["hit_rate"])
            mrrs.append(retrieval["mrr"])
            recalls.append(retrieval["recall_at_k"])

        total = len(hit_rates) or 1
        return {
            "avg_hit_rate": sum(hit_rates) / total,
            "avg_mrr": sum(mrrs) / total,
            "avg_recall_at_k": sum(recalls) / total,
        }