"""
run_eval.py
One-shot orchestrator for the full evaluation pipeline.
Usage:
  python eval/run_eval.py                    # all stages
  python eval/run_eval.py --skip-generate   # skip question generation
  python eval/run_eval.py --skip-collect    # skip response collection
  python eval/run_eval.py --only-report     # just show the report
  python eval/run_eval.py --api-url http://localhost:8000/api/v1/chat
"""

import os
import sys
import argparse
import asyncio
import subprocess
import time
from pathlib import Path

EVAL_DIR = Path(__file__).parent
ROOT = EVAL_DIR.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("CHAT_API_URL", "http://localhost:8000/api/v1/chat")


def banner(title: str):
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


async def run_generate():
    banner("Stage 1 / 3 — Generate Questions")
    from eval.generate_questions import main as gen_main
    await gen_main()


async def run_collect(api_url: str):
    banner("Stage 2 / 3 — Collect System Responses")
    os.environ["CHAT_API_URL"] = api_url
    # Re-import to pick up env
    import importlib, eval.collect_responses as cr
    importlib.reload(cr)
    await cr.main()


def run_grade():
    banner("Stage 3a / 3 — Grade Responses (LLM-as-Judge)")
    import importlib, eval.grade_responses as gr
    importlib.reload(gr)
    # Use run_until_complete to avoid "asyncio.run() cannot be called from a running event loop"
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, gr.main())
            future.result()
    else:
        loop.run_until_complete(gr.main())



def run_report():
    banner("Stage 3b / 3 — Generate Report")
    import importlib, eval.report as rp
    importlib.reload(rp)
    rp.main()


async def run_all(args):
    start = time.time()

    if not args.skip_generate and not args.only_report:
        await run_generate()

    if not args.skip_collect and not args.only_report:
        await run_collect(args.api_url)

    if not args.only_collect:
        run_grade()
        run_report()

    elapsed = time.time() - start
    print(f"\n✅ Full eval pipeline completed in {elapsed:.1f}s")
    print(f"   Check: eval/eval_report.md for the full report")


def main():
    parser = argparse.ArgumentParser(description="HCP Pharma Assistant — Full Eval Pipeline")
    parser.add_argument("--skip-generate", action="store_true", help="Skip question generation")
    parser.add_argument("--skip-collect", action="store_true", help="Skip response collection")
    parser.add_argument("--only-report", action="store_true", help="Only run report (skips gen+collect+grade)")
    parser.add_argument("--only-collect", action="store_true", help="Run gen+collect only (no grading)")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1/chat",
                        help="Base URL for the chat API (default: http://localhost:8000/api/v1/chat)")
    args = parser.parse_args()

    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + "  🧪 HCP Pharma Assistant — Evaluation Suite".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print(f"\n  API URL : {args.api_url}")
    print(f"  Mode    : ", end="")
    if args.only_report:
        print("Report only")
    elif args.only_collect:
        print("Generate + Collect only")
    elif args.skip_generate and args.skip_collect:
        print("Grade + Report only")
    else:
        print("Full pipeline")

    asyncio.run(run_all(args))


if __name__ == "__main__":
    main()
