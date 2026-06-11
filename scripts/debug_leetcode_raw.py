"""
Raw LeetCode contest-history dump for one handle. Diagnostic only — no DB,
no filtering. Prints exactly what the GraphQL endpoint returns so we can see
whether a "0 contests" result is a handle problem, a window problem, or an
attended-flag (not-yet-finalized) problem.

Usage:
    uv run --python 3.12 scripts/debug_leetcode_raw.py <lc_handle>
    uv run --python 3.12 scripts/debug_leetcode_raw.py Swastika-IT
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

QUERY = """
query debug($username: String!) {
  matchedUser(username: $username) { username }
  userContestRanking(username: $username) {
    attendedContestsCount
    rating
    globalRanking
  }
  userContestRankingHistory(username: $username) {
    attended
    rating
    ranking
    contest { title titleSlug startTime }
  }
}
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    handle = sys.argv[1]
    print(f"Querying LeetCode for handle: {handle!r}\n")

    resp = requests.post(
        "https://leetcode.com/graphql",
        json={"query": QUERY, "variables": {"username": handle}},
        headers={"User-Agent": UA, "Content-Type": "application/json",
                 "Referer": f"https://leetcode.com/u/{handle}/"},
        timeout=15,
    )
    print(f"HTTP {resp.status_code}  content-type={resp.headers.get('content-type')}")
    try:
        payload = resp.json()
    except ValueError:
        print("\n!! Response is NOT JSON — likely blocked. First 600 chars:\n")
        print(resp.text[:600])
        return 1

    if "errors" in payload:
        print("\n!! GraphQL returned errors:")
        print(json.dumps(payload["errors"], indent=2))

    data = payload.get("data") or {}

    matched = data.get("matchedUser")
    print("\nmatchedUser:")
    if matched is None:
        print(f"  None  ← LeetCode has NO user for handle {handle!r}.")
        print("         The registered lc_handle is wrong/misspelled/wrong case.")
    else:
        canonical = matched.get("username")
        print(f"  username = {canonical!r}")
        if canonical and canonical != handle:
            print(f"  NOTE: stored handle {handle!r} != canonical {canonical!r}")

    summary = data.get("userContestRanking")
    print("\nuserContestRanking (summary):")
    if summary is None:
        print("  None  ← user has no rated-contest record at all.")
    else:
        print(f"  attendedContestsCount = {summary.get('attendedContestsCount')}")
        print(f"  rating                = {summary.get('rating')}")

    history = data.get("userContestRankingHistory")
    if history is None:
        print("\nuserContestRankingHistory: None")
        return 0

    attended = [h for h in history if h.get("attended")]
    print(f"\nhistory rows total    = {len(history)}")
    print(f"history rows attended = {len(attended)}")

    if not attended:
        print("\nNo rows with attended=true. If she really participated, either the")
        print("handle points at the wrong account, or LeetCode hasn't finalized the")
        print("contest yet (the row reads attended=false until it's rated, ~1 day).")
        return 0

    print("\nAttended contests (title | startTime UTC | rating | rank):")
    for h in sorted(attended, key=lambda r: int(r["contest"]["startTime"])):
        c = h["contest"]
        dt = datetime.fromtimestamp(int(c["startTime"]), tz=timezone.utc)
        print(f"  {c.get('title',''):35} | {dt.isoformat()} | "
              f"rating={h.get('rating')} | rank={h.get('ranking')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
