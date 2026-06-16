import asyncio
import json
import os
import statistics
import time
from typing import Dict, List, Tuple

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner

QUALITY_THRESHOLDS = {
    "min_avg_score": 3.5,
    "min_hit_rate": 0.78,
    "min_agreement_rate": 0.65,
    "max_avg_latency": 0.5,
    "max_cost_regression_pct": 30.0,
}


def load_dataset() -> List[Dict]:
    if not os.path.exists("data/golden_set.jsonl"):
        raise FileNotFoundError(
            "Missing data/golden_set.jsonl. Run 'python data/synthetic_gen.py' first."
        )

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if len(dataset) < 50:
        raise ValueError(
            f"Golden dataset must contain at least 50 cases; found {len(dataset)}."
        )

    required = {"question", "expected_answer", "expected_retrieval_ids", "metadata"}
    for index, case in enumerate(dataset, start=1):
        missing = required - set(case)
        if missing:
            raise ValueError(
                f"Case #{index} is missing required fields: {sorted(missing)}"
            )
    return dataset


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def summarize(version: str, results: List[Dict], duration: float) -> Dict:
    total = len(results)
    scores = [r["judge"]["final_score"] for r in results]
    hit_rates = [r["ragas"]["retrieval"]["hit_rate"] for r in results]
    mrrs = [r["ragas"]["retrieval"]["mrr"] for r in results]
    recalls = [r["ragas"]["retrieval"]["recall_at_k"] for r in results]
    agreements = [r["judge"]["agreement_rate"] for r in results]
    faithfulness = [r["ragas"]["faithfulness"] for r in results]
    relevancy = [r["ragas"]["relevancy"] for r in results]
    latencies = [r["latency"] for r in results]
    tokens = [r["tokens_used"] for r in results]
    costs = [r["estimated_cost_usd"] for r in results]
    failures = [r for r in results if r["status"] == "fail"]

    by_type: Dict[str, Dict[str, float]] = {}
    for result in results:
        case_type = result["metadata"]["case"].get("type", "unknown")
        bucket = by_type.setdefault(
            case_type, {"total": 0, "fail": 0, "score_sum": 0.0}
        )
        bucket["total"] += 1
        bucket["fail"] += 1 if result["status"] == "fail" else 0
        bucket["score_sum"] += result["judge"]["final_score"]

    for bucket in by_type.values():
        bucket["avg_score"] = round(bucket["score_sum"] / bucket["total"], 4)
        del bucket["score_sum"]

    return {
        "metadata": {
            "version": version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(duration, 4),
        },
        "metrics": {
            "avg_score": round(sum(scores) / total, 4),
            "median_score": round(statistics.median(scores), 4),
            "pass_rate": round((total - len(failures)) / total, 4),
            "hit_rate": round(sum(hit_rates) / total, 4),
            "mrr": round(sum(mrrs) / total, 4),
            "recall_at_k": round(sum(recalls) / total, 4),
            "faithfulness": round(sum(faithfulness) / total, 4),
            "relevancy": round(sum(relevancy) / total, 4),
            "agreement_rate": round(sum(agreements) / total, 4),
            "avg_latency_seconds": round(sum(latencies) / total, 4),
            "p95_latency_seconds": round(percentile(latencies, 95), 4),
            "total_tokens": sum(tokens),
            "avg_tokens": round(sum(tokens) / total, 2),
            "estimated_cost_usd": round(sum(costs), 6),
            "failed_cases": len(failures),
        },
        "breakdown_by_type": by_type,
    }


def release_gate(v1_summary: Dict, v2_summary: Dict) -> Dict:
    v1 = v1_summary["metrics"]
    v2 = v2_summary["metrics"]
    score_delta = v2["avg_score"] - v1["avg_score"]
    hit_rate_delta = v2["hit_rate"] - v1["hit_rate"]
    latency_delta = v2["avg_latency_seconds"] - v1["avg_latency_seconds"]
    cost_delta = v2["estimated_cost_usd"] - v1["estimated_cost_usd"]
    cost_regression_pct = (
        0.0
        if v1["estimated_cost_usd"] == 0
        else (cost_delta / v1["estimated_cost_usd"]) * 100
    )

    checks = {
        "quality_floor": v2["avg_score"] >= QUALITY_THRESHOLDS["min_avg_score"],
        "retrieval_floor": v2["hit_rate"] >= QUALITY_THRESHOLDS["min_hit_rate"],
        "judge_reliability_floor": v2["agreement_rate"]
        >= QUALITY_THRESHOLDS["min_agreement_rate"],
        "latency_floor": v2["avg_latency_seconds"]
        <= QUALITY_THRESHOLDS["max_avg_latency"],
        "non_negative_quality_delta": score_delta >= -0.05,
        "cost_regression_limit": cost_regression_pct
        <= QUALITY_THRESHOLDS["max_cost_regression_pct"],
    }

    return {
        "decision": "APPROVE" if all(checks.values()) else "BLOCK_RELEASE",
        "checks": checks,
        "thresholds": QUALITY_THRESHOLDS,
        "delta": {
            "avg_score": round(score_delta, 4),
            "hit_rate": round(hit_rate_delta, 4),
            "avg_latency_seconds": round(latency_delta, 4),
            "estimated_cost_usd": round(cost_delta, 6),
            "cost_regression_pct": round(cost_regression_pct, 2),
        },
    }


async def run_benchmark(
    agent: MainAgent, version: str, dataset: List[Dict]
) -> Tuple[List[Dict], Dict]:
    print(f"Khoi dong benchmark cho {version}...")
    runner = BenchmarkRunner(agent, RetrievalEvaluator(), LLMJudge())
    start = time.perf_counter()
    results = await runner.run_all(dataset, batch_size=10)
    duration = time.perf_counter() - start
    return results, summarize(version, results, duration)


async def main():
    try:
        dataset = load_dataset()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Khong the chay benchmark: {exc}")
        return

    v1_agent = MainAgent(
        name="SupportAgent-v1-base", top_k=1, threshold=0.18, strict_grounding=False
    )
    v2_agent = MainAgent(
        name="SupportAgent-v2-optimized", top_k=2, threshold=0.12, strict_grounding=True
    )

    v1_results, v1_summary = await run_benchmark(v1_agent, "Agent_V1_Base", dataset)
    v2_results, v2_summary = await run_benchmark(
        v2_agent, "Agent_V2_Optimized", dataset
    )
    gate = release_gate(v1_summary, v2_summary)
    v2_summary["regression"] = {
        "baseline": v1_summary,
        "release_gate": gate,
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "baseline_results": v1_results,
                "candidate_results": v2_results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n--- KET QUA SO SANH REGRESSION ---")
    print(f"V1 avg_score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 avg_score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta score: {gate['delta']['avg_score']:+.4f}")
    print(f"V2 hit_rate: {v2_summary['metrics']['hit_rate']}")
    print(f"V2 agreement_rate: {v2_summary['metrics']['agreement_rate']}")
    print(f"V2 estimated_cost_usd: {v2_summary['metrics']['estimated_cost_usd']}")
    print(f"QUYET DINH: {gate['decision']}")
    print("Reports saved to reports/summary.json and reports/benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(main())
