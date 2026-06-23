import argparse
import json
import re
import time
from statistics import mean

from models import client, MODEL


def exclamation_ratio(text: str) -> float:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return 0.0
    return round(text.count("!") / len(compact), 4)


def run_case(model: str, case: dict, runs: int) -> dict:
    attempts = []
    for _ in range(runs):
        start = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=case["messages"],
            temperature=case["temperature"],
            max_tokens=case["max_tokens"],
        )
        text = resp.choices[0].message.content or ""
        attempts.append(
            {
                "latency_s": round(time.time() - start, 2),
                "finish_reason": resp.choices[0].finish_reason,
                "response_len": len(text),
                "exclaim_ratio": exclamation_ratio(text),
                "preview": text[:120],
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            }
        )

    return {
        "avg_latency_s": round(mean(a["latency_s"] for a in attempts), 2),
        "exclaim_loop_runs": sum(1 for a in attempts if a["exclaim_ratio"] >= 0.95),
        "finish_reasons": sorted(set(a["finish_reason"] for a in attempts)),
        "runs": attempts,
    }


def build_cases() -> dict:
    repetitive_doc = "\n".join(
        ["CONFIDENTIAL REPORT", "Revenue 12 Cost 3 Risk 4", "Footer 2026"] * 120
    )
    boardroom_doc = " ".join(
        [f"Section {i}: revenue {i%17}, risk {i%9}, mitigation {i%5}." for i in range(1, 140)]
    )

    return {
        "short_control": {
            "messages": [
                {"role": "system", "content": "You are concise."},
                {"role": "user", "content": "Reply with exactly: OK"},
            ],
            "temperature": 0.0,
            "max_tokens": 16,
        },
        "medium_summary": {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {
                    "role": "user",
                    "content": "Summarize in 3 bullets:\n"
                    + ("Point A revenue up, risk down, hiring stable. " * 20),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 120,
        },
        "repetitive_pdf_like": {
            "messages": [
                {"role": "system", "content": "You are the Analyst."},
                {
                    "role": "user",
                    "content": (
                        "Here is the document you must analyse:\n\n"
                        f"{repetitive_doc}\n\n---\n"
                        "Extract 3 key facts as numbered list. Cite [p.X]."
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 220,
        },
        "boardroom_like": {
            "messages": [
                {"role": "system", "content": "You are the Analyst."},
                {
                    "role": "user",
                    "content": (
                        "Here is the document you must analyse:\n\n"
                        f"{boardroom_doc}\n\n---\n"
                        "Extract 3 key facts as numbered list. Cite [p.X]."
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 220,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark output stability across models.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=[MODEL],
        help="Model IDs to benchmark against the configured API endpoint.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="How many runs per case per model.",
    )
    parser.add_argument(
        "--out",
        default="benchmark_results.json",
        help="Output JSON file path.",
    )
    args = parser.parse_args()

    cases = build_cases()
    report = {"models": {}}
    for model in args.models:
        report["models"][model] = {}
        for case_name, case in cases.items():
            report["models"][model][case_name] = run_case(model, case, args.runs)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps({"saved": args.out, "models": args.models}, indent=2))


if __name__ == "__main__":
    main()
