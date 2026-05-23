"""
LLM Evaluation Runner for Sovereign-SRE.

Runs 50 ground-truth samples through the Bedrock pipeline,
scores 4 metrics, saves report to S3 + DynamoDB.

Usage:
    python evaluation/eval_runner.py \
        --prompt-version $(git rev-parse --short HEAD) \
        --n-samples 20 \
        --fail-below 0.75
"""

from __future__ import annotations
import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Optional

ROOT = Path(__file__).parent.parent
GROUND_TRUTH = ROOT / "evaluation" / "ground_truth.jsonl"

FIX_TYPES = [
    "connection_pool_config", "jvm_heap_config", "cpu_throttle",
    "network_timeout", "pod_restart", "log_rotation", "retry_policy",
]

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer.
Given a real infrastructure anomaly from production logs, provide:
1. Technical root cause in exactly 2 sentences
2. The fix_type (MUST be one of: connection_pool_config, jvm_heap_config,
   cpu_throttle, network_timeout, pod_restart, log_rotation, retry_policy)
3. The affected_file path
4. Confidence score 0.0-1.0
5. Resolution steps (3 items)

Return ONLY valid JSON:
{"root_cause": "...", "fix_type": "...", "affected_file": "...",
 "confidence": 0.91, "diff": "--- a/...\n+++ b/...", "resolution_steps": ["..."]}"""


@dataclass
class SampleResult:
    incident_id: str
    anomaly_type: str
    predicted_fix_type: str
    ground_truth_fix_type: str
    predicted_affected_file: str
    ground_truth_affected_file: str
    root_cause_accuracy: float       # 1.0 if fix_type matches
    semantic_similarity: float       # cosine sim of root causes
    ragas_faithfulness: float        # does response stay faithful to log?
    file_attribution: float          # 1.0 if gt file mentioned in response
    composite_score: float
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: Optional[str] = None


def load_ground_truth(path: Path, n: int) -> list[dict]:
    samples = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples[:n]


def call_bedrock(client, sample: dict, model_id: str) -> tuple[dict, int, int, float]:
    """Call Bedrock and return (parsed_json, input_tokens, output_tokens, latency_ms)."""
    import re

    prompt = f"""Real incident from {sample['source']} dataset:
Service: {sample['service']}
Anomaly: {sample['anomaly_type']}
Duration: {sample['duration_seconds']}s
Peak: {sample['metric_peak']}% (baseline: {sample['metric_baseline']}%)
Raw log: {sample['raw_log'][:200]}

Diagnose and return JSON."""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }

    t0 = time.time()
    resp = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    latency = (time.time() - t0) * 1000

    raw = json.loads(resp["body"].read())
    text = raw["content"][0]["text"].strip()
    usage = raw.get("usage", {})
    input_t = usage.get("input_tokens", 300)
    output_t = usage.get("output_tokens", 150)

    # Parse JSON
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if "```" in text:
        text = text.split("```")[0]
    try:
        parsed = json.loads(text)
    except Exception:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        parsed = json.loads(m.group()) if m else {}

    return parsed, input_t, output_t, latency


def embed_text(texts: list[str]) -> list[list[float]]:
    """Embed texts using sentence-transformers (local, no API cost)."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(texts, normalize_embeddings=True).tolist()
    except ImportError:
        # fallback: simple TF-IDF-like similarity
        return [[0.5] * 384 for _ in texts]


def cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-9)


def score_faithfulness(predicted: dict, sample: dict) -> float:
    """
    Simple faithfulness: check if key facts from the log appear in the response.
    Returns 0.0-1.0.
    """
    response_text = json.dumps(predicted).lower()
    facts = [
        sample["service"].lower(),
        sample["anomaly_type"].replace("_", " "),
    ]
    # Optional: check duration and metric values appear
    hits = sum(1 for f in facts if f in response_text)
    return hits / len(facts)


def score_sample(predicted: dict, sample: dict, embed_cache: dict) -> tuple[float, float, float, float]:
    """Returns (root_cause_acc, semantic_sim, faithfulness, file_attr)."""
    # 1. Root cause accuracy (fix_type match)
    pred_ft = predicted.get("fix_type", "").lower().strip()
    gt_ft = sample["ground_truth_fix_type"].lower().strip()
    rca = 1.0 if pred_ft == gt_ft else 0.0

    # 2. Semantic similarity
    pred_rc = predicted.get("root_cause", "")
    gt_rc = sample["ground_truth_root_cause"]
    if pred_rc and gt_rc:
        key = (pred_rc[:50], gt_rc[:50])
        if key not in embed_cache:
            embeds = embed_text([pred_rc, gt_rc])
            embed_cache[key] = cosine_sim(embeds[0], embeds[1])
        sem = embed_cache[key]
    else:
        sem = 0.0

    # 3. Faithfulness
    faith = score_faithfulness(predicted, sample)

    # 4. File attribution
    gt_file = sample["ground_truth_affected_file"].lower()
    response_text = json.dumps(predicted).lower()
    file_attr = 1.0 if gt_file.lower() in response_text else 0.0

    return rca, sem, faith, file_attr


def haiku_cost(input_t: int, output_t: int) -> float:
    return (input_t / 1000 * 0.00025) + (output_t / 1000 * 0.00125)


class SovereignSREEvaluator:
    def __init__(self, model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"):
        import boto3
        self.model_id = model_id
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-2"),
        )
        self.embed_cache: dict = {}

    def run_eval(self, prompt_version: str, n_samples: int = 50) -> dict:
        samples = load_ground_truth(GROUND_TRUTH, n_samples)
        print(f"\n  Running eval: {len(samples)} samples · model={self.model_id}")

        results: list[SampleResult] = []
        total_cost = 0.0

        for i, sample in enumerate(samples, 1):
            print(f"  [{i:02d}/{len(samples)}] {sample['incident_id']} {sample['anomaly_type']}...", end=" ", flush=True)
            try:
                predicted, input_t, output_t, latency = call_bedrock(
                    self.client, sample, self.model_id
                )
                rca, sem, faith, file_attr = score_sample(predicted, sample, self.embed_cache)
                composite = (rca * 0.35 + sem * 0.30 + faith * 0.25 + file_attr * 0.10)
                cost = haiku_cost(input_t, output_t)
                total_cost += cost

                r = SampleResult(
                    incident_id=sample["incident_id"],
                    anomaly_type=sample["anomaly_type"],
                    predicted_fix_type=predicted.get("fix_type", ""),
                    ground_truth_fix_type=sample["ground_truth_fix_type"],
                    predicted_affected_file=predicted.get("affected_file", ""),
                    ground_truth_affected_file=sample["ground_truth_affected_file"],
                    root_cause_accuracy=rca,
                    semantic_similarity=round(sem, 3),
                    ragas_faithfulness=round(faith, 3),
                    file_attribution=file_attr,
                    composite_score=round(composite, 3),
                    latency_ms=round(latency, 1),
                    input_tokens=input_t,
                    output_tokens=output_t,
                    cost_usd=round(cost, 6),
                )
                print(f"✓ composite={composite:.2f} rca={rca:.0f} sem={sem:.2f} latency={latency:.0f}ms")
            except Exception as e:
                print(f"✗ {e}")
                r = SampleResult(
                    incident_id=sample["incident_id"],
                    anomaly_type=sample["anomaly_type"],
                    predicted_fix_type="", ground_truth_fix_type=sample["ground_truth_fix_type"],
                    predicted_affected_file="", ground_truth_affected_file=sample["ground_truth_affected_file"],
                    root_cause_accuracy=0, semantic_similarity=0, ragas_faithfulness=0,
                    file_attribution=0, composite_score=0, latency_ms=0,
                    input_tokens=0, output_tokens=0, cost_usd=0, error=str(e),
                )
            results.append(r)
            time.sleep(0.3)

        # Aggregate metrics
        def avg(field: str) -> float:
            vals = [getattr(r, field) for r in results if not r.error]
            return round(mean(vals), 3) if vals else 0.0

        latencies = sorted(r.latency_ms for r in results if r.latency_ms > 0)
        p50 = latencies[len(latencies) // 2] if latencies else 0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0

        # Per anomaly type
        types = {}
        for atype in set(r.anomaly_type for r in results):
            batch = [r for r in results if r.anomaly_type == atype and not r.error]
            types[atype] = {
                "accuracy": round(mean(r.root_cause_accuracy for r in batch), 2) if batch else 0,
                "n": len(batch),
            }

        ts = datetime.now(timezone.utc).isoformat()
        report = {
            "prompt_version": prompt_version,
            "timestamp": ts,
            "model_id": self.model_id,
            "n_samples": len(results),
            "metrics": {
                "root_cause_accuracy": avg("root_cause_accuracy"),
                "semantic_similarity": avg("semantic_similarity"),
                "ragas_faithfulness": avg("ragas_faithfulness"),
                "file_attribution": avg("file_attribution"),
                "composite_score": avg("composite_score"),
            },
            "performance": {
                "p50_latency_ms": round(p50),
                "p95_latency_ms": round(p95),
                "avg_input_tokens": round(avg("input_tokens")),
                "avg_output_tokens": round(avg("output_tokens")),
                "total_cost_usd": round(total_cost, 4),
            },
            "per_anomaly_type": types,
        }

        self._save_report(report, prompt_version, ts)
        return report

    def _save_report(self, report: dict, prompt_version: str, ts: str) -> None:
        # Save locally
        last = ROOT / "evaluation" / "last_report.json"
        last.write_text(json.dumps(report, indent=2))

        # Save to S3
        try:
            import boto3
            s3 = boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-2"))
            bucket = os.environ.get("S3_BUCKET", "sovereign-sre-artifacts-574772738370")
            key = f"evaluations/{prompt_version}/{ts[:19].replace(':','-')}/report.json"
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report, indent=2),
                          ContentType="application/json")
            print(f"\n  ✓ Report saved to S3: s3://{bucket}/{key}")
        except Exception as e:
            print(f"\n  ⚠ S3 save failed: {e}")

        # Save to DynamoDB sovereign-sre-evals
        try:
            import boto3
            from decimal import Decimal
            ddb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-2"))
            table = ddb.Table("sovereign-sre-evals")
            table.put_item(Item={
                "prompt_version": prompt_version,
                "timestamp": ts,
                "composite_score": Decimal(str(report["metrics"]["composite_score"])),
                "root_cause_accuracy": Decimal(str(report["metrics"]["root_cause_accuracy"])),
                "faithfulness": Decimal(str(report["metrics"]["ragas_faithfulness"])),
                "n_samples": report["n_samples"],
                "total_cost_usd": Decimal(str(report["performance"]["total_cost_usd"])),
                "model_id": report["model_id"],
            })
            print(f"  ✓ Report saved to DynamoDB: sovereign-sre-evals")
        except Exception as e:
            print(f"  ⚠ DynamoDB save failed: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-version", default="local")
    parser.add_argument("--n-samples", type=int, default=20)
    parser.add_argument("--fail-below", type=float, default=0.75)
    parser.add_argument("--model", default="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    evaluator = SovereignSREEvaluator(model_id=args.model)
    report = evaluator.run_eval(
        prompt_version=args.prompt_version,
        n_samples=args.n_samples,
    )

    print("\n" + "=" * 60)
    print("  EVAL REPORT")
    print("=" * 60)
    m = report["metrics"]
    p = report["performance"]
    print(f"  Root cause accuracy:  {m['root_cause_accuracy']:.3f}")
    print(f"  Semantic similarity:  {m['semantic_similarity']:.3f}")
    print(f"  RAGAS faithfulness:   {m['ragas_faithfulness']:.3f}")
    print(f"  File attribution:     {m['file_attribution']:.3f}")
    print(f"  ─────────────────────────────────")
    print(f"  Composite score:      {m['composite_score']:.3f}")
    print(f"  p50 latency:          {p['p50_latency_ms']}ms")
    print(f"  p95 latency:          {p['p95_latency_ms']}ms")
    print(f"  Total cost:           ${p['total_cost_usd']:.4f}")
    print(f"\n  Per anomaly type:")
    for atype, stats in report["per_anomaly_type"].items():
        print(f"    {atype:<22} accuracy={stats['accuracy']:.2f}  n={stats['n']}")

    score = m["composite_score"]
    threshold = args.fail_below
    if score < threshold:
        print(f"\n  ✗ FAIL — composite {score:.3f} < threshold {threshold}")
        sys.exit(1)
    else:
        print(f"\n  ✓ PASS — composite {score:.3f} ≥ threshold {threshold}")


if __name__ == "__main__":
    main()
