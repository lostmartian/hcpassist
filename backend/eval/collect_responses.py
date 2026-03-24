"""
collect_responses.py
Sends all questions to the running /api/v1/chat endpoint in parallel.
- Max 5 concurrent workers (throttled to protect LLM backend)
- Progressive writes: saves each response immediately after receiving it
- Resumable: on restart, retries questions that errored OR were never collected
- Retry: each question is attempted up to 3 times with exponential backoff
"""

import os
import sys
import json
import asyncio
import time
import httpx
from pathlib import Path

EVAL_DIR = Path(__file__).parent
QUESTIONS_FILE = EVAL_DIR / "questions.json"
RESPONSES_FILE = EVAL_DIR / "system_responses.json"

API_URL = os.environ.get("CHAT_API_URL", "http://localhost:8000/api/v1/chat")
MAX_CONCURRENCY = 5
TIMEOUT_SEC = 120       # some questions may require multi-step RAG
MAX_RETRIES = 3         # per-question retry attempts
RETRY_BACKOFF = [2, 5]  # seconds to wait between retries (attempt 1→2, 2→3)


# ─────────────────────────────────────────────
# I/O HELPERS
# ─────────────────────────────────────────────

def load_questions() -> list:
    if not QUESTIONS_FILE.exists():
        print(f"❌ {QUESTIONS_FILE} not found. Run generate_questions.py first.")
        sys.exit(1)
    with open(QUESTIONS_FILE) as f:
        return json.load(f)


def load_existing_responses() -> dict:
    """
    Return dict of id -> response.
    Only entries with status == 'ok' are considered done.
    Entries with error status are treated as pending (will be retried).
    """
    if RESPONSES_FILE.exists():
        with open(RESPONSES_FILE) as f:
            data = json.load(f)
        return {r["id"]: r for r in data}
    return {}


def is_done(entry: dict) -> bool:
    """An entry is 'done' only when it succeeded."""
    return entry.get("status") == "ok"


_write_lock = asyncio.Lock()


async def save_response(existing: dict, item: dict):
    """Thread-safe upsert + flush to disk."""
    async with _write_lock:
        existing[item["id"]] = item
        with open(RESPONSES_FILE, "w") as f:
            json.dump(list(existing.values()), f, indent=2)


# ─────────────────────────────────────────────
# REQUEST WORKER  (retry-aware)
# ─────────────────────────────────────────────

async def fetch_response(semaphore, client, q: dict, existing: dict, progress: dict):
    """
    Fetch a single question's response with up to MAX_RETRIES attempts.
    Writes the result (success or final error) to disk immediately.
    """
    qid = q["id"]

    async with semaphore:
        attempt = 0
        last_error = ""
        item = None

        while attempt < MAX_RETRIES:
            attempt += 1
            start = time.time()
            try:
                resp = await client.post(
                    API_URL,
                    json={"message": q["question"]},
                    timeout=TIMEOUT_SEC,
                )
                resp.raise_for_status()
                data = resp.json()
                elapsed_ms = round((time.time() - start) * 1000)

                item = {
                    "id": qid,
                    "category": q["category"],
                    "question": q["question"],
                    "ground_truth": q["ground_truth"],
                    "system_response": data.get("response", ""),
                    "retry_count": data.get("retry_count", 0),
                    "status": "ok",
                    "attempts": attempt,
                    "latency_ms": elapsed_ms,
                }
                break  # success — exit retry loop

            except Exception as e:
                elapsed_ms = round((time.time() - start) * 1000)
                last_error = str(e)[:180]
                retry_note = f" (attempt {attempt}/{MAX_RETRIES})" if attempt < MAX_RETRIES else ""
                print(
                    f"  ⚠️  [{qid}] attempt {attempt} failed{retry_note}: {last_error[:80]}",
                    flush=True,
                )
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                    await asyncio.sleep(wait)

        # All attempts exhausted → record final error
        if item is None:
            item = {
                "id": qid,
                "category": q["category"],
                "question": q["question"],
                "ground_truth": q["ground_truth"],
                "system_response": "",
                "retry_count": 0,
                "status": f"error: {last_error}",
                "attempts": attempt,
                "latency_ms": 0,
            }

        await save_response(existing, item)

        progress["done"] += 1
        total = progress["total"]
        done = progress["done"]
        pct = int(done / total * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        status_icon = "✓" if item["status"] == "ok" else "✗"
        attempts_note = f" (x{item['attempts']})" if item["attempts"] > 1 else ""
        print(
            f"  [{bar}] {done:3d}/{total} {pct:3d}%  "
            f"{status_icon} [{qid}]{attempts_note} {item.get('latency_ms', 0)}ms",
            flush=True,
        )
        return item


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  HCP Pharma Assistant — Response Collector")
    print("=" * 60)

    questions = load_questions()
    existing = load_existing_responses()

    # Separate truly done vs needs-processing (never fetched OR errored)
    done_ids   = {qid for qid, r in existing.items() if is_done(r)}
    error_ids  = {qid for qid, r in existing.items() if not is_done(r)}
    pending    = [q for q in questions if q["id"] not in done_ids]

    print(f"\n  Total questions : {len(questions)}")
    print(f"  ✅ Already done  : {len(done_ids)}")
    print(f"  ⚠️  Errored/retry : {len(error_ids)}")
    print(f"  → Pending now   : {len(pending)}")
    print(f"  API URL         : {API_URL}")
    print(f"  Concurrency     : {MAX_CONCURRENCY}  |  Max retries: {MAX_RETRIES}")

    if not pending:
        print("\n  ✅ All responses already collected successfully. Nothing to do.")
        return

    # Health check
    try:
        async with httpx.AsyncClient() as hc_client:
            hc = await hc_client.get(API_URL.replace("/chat", "/health"), timeout=10)
            hc.raise_for_status()
        print(f"\n  ✅ API health check passed")
    except Exception as e:
        print(f"\n  ❌ API health check failed: {e}")
        print("     Make sure the server is running: python main.py")
        sys.exit(1)

    print(f"\n  Collecting responses (parallel, resumable, retrying errors)...\n")

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    progress = {"done": 0, "total": len(pending)}

    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_response(semaphore, client, q, existing, progress)
            for q in pending
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    ok_items   = [r for r in results if isinstance(r, dict) and r.get("status") == "ok"]
    err_items  = [r for r in results if isinstance(r, dict) and r.get("status", "").startswith("error")]
    exceptions = [r for r in results if isinstance(r, Exception)]

    print(f"\n{'=' * 60}")
    print(f"  ✅ Collected : {len(ok_items)}")
    print(f"  ❌ Errors    : {len(err_items) + len(exceptions)}")
    print(f"  Total in file: {len(existing)}/{len(questions)}")
    if err_items:
        print(f"\n  ⚠️  Errored IDs (re-run to retry):")
        for r in err_items:
            print(f"     [{r['id']}] {r['status'][:80]}")

    # Latency stats for successful ones
    latencies = [r.get("latency_ms", 0) for r in ok_items if r.get("latency_ms", 0) > 0]
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"\n  Avg latency : {avg:.0f}ms | Min: {min(latencies)}ms | Max: {max(latencies)}ms")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
