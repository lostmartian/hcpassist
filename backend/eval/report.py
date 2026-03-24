"""
report.py
Reads scores.json and generates a detailed accuracy report.
Prints to console and saves eval_report.md.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

EVAL_DIR = Path(__file__).parent
SCORES_FILE = EVAL_DIR / "scores.json"
RESPONSES_FILE = EVAL_DIR / "system_responses.json"
REPORT_FILE = EVAL_DIR / "eval_report.md"

CATEGORY_LABELS = {
    "hcp_profile": "HCP Profile Lookup",
    "hcp_rx_performance": "HCP Rx Performance",
    "account_info": "Account Information",
    "rep_activity": "Rep Activity",
    "ln_metrics": "LN Metrics & Market Share",
    "payor_mix": "Payor Mix",
    "ranking_comparison": "Rankings & Comparisons",
    "trends": "Trends Over Time",
    "security_guardrail": "Security & Guardrails",
    "complex_multihop": "Complex Multi-hop",
}


def load_scores() -> list:
    if not SCORES_FILE.exists():
        print(f"❌ {SCORES_FILE} not found. Run grade_responses.py first.")
        sys.exit(1)
    with open(SCORES_FILE) as f:
        return json.load(f)


def compute_report(scores: list) -> str:
    total = len(scores)
    if total == 0:
        return "# No scores found.\n"

    correct = sum(1 for s in scores if s["grade"] == "CORRECT")
    partial = sum(1 for s in scores if s["grade"] == "PARTIAL")
    incorrect = sum(1 for s in scores if s["grade"] == "INCORRECT")
    total_score = sum(s["score"] for s in scores)
    overall_pct = total_score / total * 100

    # Category breakdown
    cat_stats = defaultdict(lambda: {"correct": 0, "partial": 0, "incorrect": 0, "score": 0.0, "n": 0})
    for s in scores:
        cat = s["category"]
        cat_stats[cat]["n"] += 1
        cat_stats[cat]["score"] += s["score"]
        if s["grade"] == "CORRECT":
            cat_stats[cat]["correct"] += 1
        elif s["grade"] == "PARTIAL":
            cat_stats[cat]["partial"] += 1
        else:
            cat_stats[cat]["incorrect"] += 1

    # Latency
    latencies = [s["latency_ms"] for s in scores if s.get("latency_ms", 0) > 0]
    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    min_lat = min(latencies) if latencies else 0
    max_lat = max(latencies) if latencies else 0

    # Failures for analysis
    failures = [s for s in scores if s["grade"] == "INCORRECT"]
    partials = [s for s in scores if s["grade"] == "PARTIAL"]

    # ── Build Markdown ──────────────────────────────
    lines = [
        "# HCP Pharma Assistant — Evaluation Report",
        "",
        "## Overall Accuracy",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Questions | {total} |",
        f"| ✅ Correct | {correct} ({correct/total*100:.1f}%) |",
        f"| 🟡 Partial | {partial} ({partial/total*100:.1f}%) |",
        f"| ❌ Incorrect | {incorrect} ({incorrect/total*100:.1f}%) |",
        f"| **Overall Score** | **{total_score:.1f}/{total} ({overall_pct:.1f}%)** |",
        f"| Avg Latency | {avg_lat:.0f}ms |",
        f"| Min / Max Latency | {min_lat}ms / {max_lat}ms |",
        "",
        "## Per-Category Breakdown",
        "",
        "| Category | Questions | ✅ | 🟡 | ❌ | Score |",
        "|----------|-----------|----|----|-----|-------|",
    ]

    for cat, stats in sorted(cat_stats.items(), key=lambda x: -x[1]["score"] / max(x[1]["n"], 1)):
        label = CATEGORY_LABELS.get(cat, cat)
        n = stats["n"]
        sc = stats["score"]
        pct = sc / n * 100 if n > 0 else 0
        lines.append(
            f"| {label} | {n} | {stats['correct']} | {stats['partial']} | {stats['incorrect']} | {sc:.1f}/{n} ({pct:.0f}%) |"
        )

    lines += [
        "",
        "## Failure Analysis",
        "",
        f"### ❌ Incorrect Responses ({len(failures)})",
        "",
    ]
    for f in failures:
        lines += [
            f"**[{f['id']}]** _{f['category']}_",
            f"> Q: {f['question']}",
            f"> Ground Truth: {f['ground_truth'][:200]}...",
            f"> System: {str(f['system_response'])[:200]}...",
            f"> Reason: {f['reason']}",
            "",
        ]

    lines += [
        f"### 🟡 Partial Responses ({len(partials)})",
        "",
    ]
    for p in partials:
        lines += [
            f"**[{p['id']}]** _{p['category']}_",
            f"> Q: {p['question']}",
            f"> Reason: {p['reason']}",
            "",
        ]

    lines += [
        "## All Results",
        "",
        "| ID | Category | Grade | Score | Reason |",
        "|----|----------|-------|-------|--------|",
    ]
    for s in sorted(scores, key=lambda x: x["id"]):
        grade_icon = {"CORRECT": "✅", "PARTIAL": "🟡", "INCORRECT": "❌"}.get(s["grade"], "?")
        reason = s.get("reason", "")[:80].replace("|", "/")
        lines.append(
            f"| {s['id']} | {s['category']} | {grade_icon} {s['grade']} | {s['score']} | {reason} |"
        )

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("  HCP Pharma Assistant — Accuracy Report")
    print("=" * 60)

    scores = load_scores()
    print(f"\n  Loaded {len(scores)} graded responses")

    report_md = compute_report(scores)

    # Save
    with open(REPORT_FILE, "w") as f:
        f.write(report_md)

    # Console summary
    total = len(scores)
    correct = sum(1 for s in scores if s["grade"] == "CORRECT")
    partial = sum(1 for s in scores if s["grade"] == "PARTIAL")
    incorrect = sum(1 for s in scores if s["grade"] == "INCORRECT")
    total_score = sum(s["score"] for s in scores)
    pct = total_score / total * 100 if total else 0

    print(f"\n  ╔══════════════════════════════════╗")
    print(f"  ║  OVERALL SCORE: {pct:5.1f}%          ║")
    print(f"  ╠══════════════════════════════════╣")
    print(f"  ║  ✅ Correct  : {correct:3d}/{total}            ║")
    print(f"  ║  🟡 Partial  : {partial:3d}/{total}            ║")
    print(f"  ║  ❌ Incorrect: {incorrect:3d}/{total}            ║")
    print(f"  ╚══════════════════════════════════╝")

    # Per-category
    from collections import defaultdict
    cat_stats = defaultdict(lambda: {"score": 0.0, "n": 0})
    for s in scores:
        cat_stats[s["category"]]["n"] += 1
        cat_stats[s["category"]]["score"] += s["score"]

    print(f"\n  Per-Category:")
    for cat, stats in sorted(cat_stats.items(), key=lambda x: -x[1]["score"] / max(x[1]["n"], 1)):
        label = CATEGORY_LABELS.get(cat, cat)
        pct_cat = stats["score"] / stats["n"] * 100
        bar = "█" * int(pct_cat / 10) + "░" * (10 - int(pct_cat / 10))
        print(f"    {bar} {pct_cat:5.1f}%  {label}")

    print(f"\n  Full report saved: {REPORT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
