#!/usr/bin/env python3
"""
Timer: type the project overview into a Markdown file over a long duration.

Usage:
    python timer.py --file overview_input.md --output overview.md --duration 4
    python timer.py --text "Hello, world!" --output overview.md --duration 0.1
    cat overview_input.md | python timer.py --output overview.md --duration 4
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


# Characters that feel slower when typed; line breaks slow the most.
CHAR_WEIGHTS: dict[str, float] = {
    "\n": 3.0,
    "\r": 3.0,
    ".": 2.0,
    "!": 2.0,
    "?": 2.0,
    ",": 1.5,
    ";": 1.5,
    ":": 1.5,
}


def _character_weight(char: str) -> float:
    return CHAR_WEIGHTS.get(char, 1.0)


def type_text(
    text: str,
    output_path: Path,
    duration_hours: float,
) -> None:
    """Type ``text`` into ``output_path`` over ``duration_hours`` hours.

    Characters are emitted one at a time with randomized delays so the final
    file grows gradually. A weighted schedule gives punctuation and line breaks
    more time without ever exceeding the requested duration.
    """
    if duration_hours <= 0:
        raise ValueError("duration_hours must be positive")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Start with a clean file.
    output_path.write_text("", encoding="utf-8")

    chars = list(text)
    if not chars:
        print("[timer] nothing to type", file=sys.stderr)
        return

    weights = [_character_weight(c) for c in chars]
    total_weight = sum(weights)
    total_seconds = duration_hours * 3600.0
    start = time.monotonic()
    deadline = start + total_seconds

    with output_path.open("a", encoding="utf-8") as f:
        cumulative_weight = 0.0
        written = 0

        try:
            for i, char in enumerate(chars):
                # Schedule this character based on its share of the total weight.
                target = start + (cumulative_weight / total_weight) * total_seconds
                cumulative_weight += weights[i]

                now = time.monotonic()
                sleep_until = min(target, deadline)
                if now < sleep_until:
                    time.sleep(sleep_until - now)

                f.write(char)
                f.flush()
                written += 1

                if (i + 1) % 50 == 0 or i == len(chars) - 1:
                    progress = (i + 1) / len(chars) * 100
                    eta = max(0.0, deadline - time.monotonic())
                    print(
                        f"[timer] {progress:.1f}% ({i + 1}/{len(chars)} chars) "
                        f"ETA: {eta / 60:.1f} min",
                        file=sys.stderr,
                    )
        except KeyboardInterrupt:
            print(f"\n[timer] interrupted after {written} characters", file=sys.stderr)
            raise SystemExit(1)

    elapsed = time.monotonic() - start
    print(
        f"[timer] finished typing {len(chars)} characters in {elapsed / 60:.1f} minutes",
        file=sys.stderr,
    )


def _read_input(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("[timer] provide --file, --text, or stdin input")


def main() -> None:
    parser = argparse.ArgumentParser(description="Type text into a Markdown file over time.")
    parser.add_argument("--file", help="Input file containing the text to type.")
    parser.add_argument("--text", help="Text string to type.")
    parser.add_argument("--output", default="overview.md", help="Output Markdown file path.")
    parser.add_argument("--duration", type=float, default=4.0, help="Duration in hours (default: 4).")
    args = parser.parse_args()

    text = _read_input(args)
    type_text(text, Path(args.output), args.duration)


if __name__ == "__main__":
    main()
