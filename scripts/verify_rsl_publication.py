"""Confirm that the public RSL page serves the exact committed data file."""
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

local_path = Path("docs/data.json")
expected_bytes = local_path.read_bytes()
expected = json.loads(expected_bytes)
if not expected.get("generated_at") or not expected.get("indexes"):
    raise RuntimeError("Committed RSL data has no valid timestamp or index data")
expected_hash = hashlib.sha256(expected_bytes).hexdigest()
url = os.environ["PAGE_URL"].rstrip("/") + "/data.json"

for attempt in range(8):
    try:
        request = urllib.request.Request(
            url + "?verify=" + str(time.time_ns()),
            headers={"Cache-Control": "no-cache", "User-Agent": "RSL-Pages-Verification"},
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            served_bytes = response.read()
        actual = json.loads(served_bytes)
        if actual.get("generated_at") != expected["generated_at"]:
            raise ValueError("RSL Pages still serves an older data generation")
        if hashlib.sha256(served_bytes).hexdigest() != expected_hash:
            raise ValueError("RSL Pages data differs from the committed file")
        summary = {
            "generated_at": actual["generated_at"],
            "indexes": len(actual["indexes"]),
            "instruments": sum(len(items) for items in actual["indexes"].values()),
            "sha256": expected_hash,
        }
        print("RSL_PAGES_VERIFIED " + json.dumps(summary))
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write("## Public RSL data verified\n```json\n" + json.dumps(summary, indent=2) + "\n```\n")
        break
    except Exception as exc:
        print(f"RSL publication check {attempt + 1}/8: {type(exc).__name__}: {exc}")
        if attempt == 7:
            raise
        time.sleep(5)
