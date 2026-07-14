#!/usr/bin/env python3
"""Run the deterministic V4 interview quality metrics over a JSON corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from content_engine.interview.quality import evaluate_corpus


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "corpus",
        nargs="?",
        default="tests/fixtures/interview_corpus/corpus.json",
    )
    args = parser.parse_args()
    payload = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    cases = payload.get("cases", []) if isinstance(payload, dict) else []
    print(json.dumps(evaluate_corpus(cases), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
