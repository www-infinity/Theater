#!/usr/bin/env python3
"""
Theater Watch Buddy
===================
An interactive AI companion that watches movies with you.

• Pops trivia facts at timed intervals during playback
• Answers any question by searching DuckDuckGo (no API key needed)
• Keeps you company throughout the film

Usage:
    python watch_buddy.py "Cartoon Network VHS Tapes"
    python watch_buddy.py --list
"""

import json
import os
import sys
import threading
import time
import textwrap
import urllib.parse
import urllib.request

FACTS_FILE = os.path.join("catalog", "facts.json")
MOVIES_FILE = os.path.join("catalog", "movies.json")

BANNER = """
╔══════════════════════════════════════════════╗
║  🎬  Theater Watch Buddy  🍿                 ║
║  Your interactive AI companion for movie night! ║
╚══════════════════════════════════════════════╝
"""

DDG_API = "https://api.duckduckgo.com/"

# Words that typically begin a question
_QUESTION_STARTERS = {
    "what", "who", "when", "where", "why", "how",
    "is", "are", "was", "were", "can", "could",
    "does", "did", "do", "will", "would", "which",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _wrap(text: str, width: int = 72, prefix: str = "") -> str:
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            lines.append(
                "\n".join(prefix + ln for ln in textwrap.wrap(paragraph, width))
            )
        else:
            lines.append("")
    return "\n".join(lines)


def _fmt_time(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


# ---------------------------------------------------------------------------
# DuckDuckGo search (Instant Answer API – no key required)
# ---------------------------------------------------------------------------

def ddg_search(query: str) -> str:
    """Query the DuckDuckGo Instant Answer API and return a readable result."""
    params = urllib.parse.urlencode(
        {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
    )
    url = f"{DDG_API}?{params}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "TheaterWatchBuddy/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return f"⚠️  Search unavailable: {exc}"

    # Try the most useful fields in descending order of preference
    if data.get("AbstractText"):
        src = data.get("AbstractSource", "")
        suffix = f" (via {src})" if src else ""
        return f"📖 {data['AbstractText']}{suffix}"

    if data.get("Answer"):
        return f"✅ {data['Answer']}"

    if data.get("Definition"):
        src = data.get("DefinitionSource", "")
        suffix = f" (via {src})" if src else ""
        return f"📚 {data['Definition']}{suffix}"

    # Fall back to related-topic snippets
    snippets = [
        t["Text"]
        for t in data.get("RelatedTopics", [])[:3]
        if isinstance(t, dict) and t.get("Text")
    ]
    if snippets:
        return "🔍 Here's what I found:\n" + "\n".join(f"  • {s}" for s in snippets)

    return (
        "🤷 No instant answer found — try rephrasing, or ask something else!\n"
        f'   Full results: https://duckduckgo.com/?q={urllib.parse.quote_plus(query)}'
    )


# ---------------------------------------------------------------------------
# Question detection
# ---------------------------------------------------------------------------

def _is_question(text: str) -> bool:
    """Return True when the input looks like a search / question."""
    stripped = text.strip().lower()
    if stripped.endswith("?"):
        return True
    if stripped.startswith("search ") or stripped.startswith("look up "):
        return True
    first = stripped.split()[0] if stripped.split() else ""
    return first in _QUESTION_STARTERS


def _normalize_query(text: str) -> str:
    stripped = text.strip()
    for prefix in ("search ", "look up ", "Search ", "Look up "):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break
    return stripped.rstrip("?").strip()


# ---------------------------------------------------------------------------
# Watch session
# ---------------------------------------------------------------------------

class WatchSession:
    """Manages timed facts and the interactive chat loop."""

    def __init__(self, title: str, facts: list):
        self.title = title
        self.facts = sorted(facts, key=lambda f: f.get("offset_seconds", 0))
        self._start: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # --- timing helpers ---

    def _elapsed(self) -> float:
        return time.monotonic() - self._start if self._start is not None else 0.0

    # --- background fact-delivery thread ---

    def _facts_worker(self) -> None:
        pending = list(self.facts)
        while pending and not self._stop.is_set():
            target = pending[0].get("offset_seconds", 0)
            # Wait until the playback clock reaches the fact's offset
            while self._elapsed() < target:
                if self._stop.wait(timeout=0.5):
                    return
            if not self._stop.is_set():
                elapsed_str = _fmt_time(self._elapsed())
                fact_text = pending[0]["fact"]
                print(
                    f"\n\n  ⭐  [{elapsed_str}]  Fun fact!\n"
                    f"{_wrap(fact_text, width=68, prefix='  ')}\n"
                    f"\n> ",
                    end="",
                    flush=True,
                )
            pending.pop(0)

    # --- lifecycle ---

    def start(self) -> None:
        self._start = time.monotonic()
        self._stop.clear()
        self._thread = threading.Thread(target=self._facts_worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # --- chat response ---

    def chat(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return ""

        lower = text.lower()

        # Quit
        if lower in {"bye", "quit", "exit", "q", "stop"}:
            return "QUIT"

        # Help
        if lower in {"help", "commands"}:
            return (
                "  Commands you can use:\n"
                "  • Ask any question         → I'll search DuckDuckGo for you\n"
                "  • 'search <topic>'         → explicit DuckDuckGo lookup\n"
                "  • 'facts'                  → list all facts for this movie\n"
                "  • 'time'                   → show elapsed playback time\n"
                "  • 'quit'                   → end the watch session\n"
            )

        # Show all facts
        if lower in {"facts", "list facts", "show facts"}:
            if not self.facts:
                return "  No pre-loaded facts for this movie — but ask me anything!"
            lines = [
                f"  [{_fmt_time(f.get('offset_seconds', 0))}]  {f['fact']}"
                for f in self.facts
            ]
            return "  📋 Facts for \"" + self.title + '":\n' + "\n\n".join(lines)

        # Elapsed time
        if lower in {"time", "how long", "elapsed", "clock"}:
            return f"  ⏱️  Elapsed: {_fmt_time(self._elapsed())}"

        # DuckDuckGo search
        if _is_question(text):
            query = _normalize_query(text)
            print(f'  🔎  Searching DuckDuckGo for "{query}"…', flush=True)
            answer = ddg_search(query)
            return _wrap(answer, width=70, prefix="  ")

        # Generic conversational reply
        return (
            "  🤖  I'm here watching with you! Ask me anything — "
            "I'll search DuckDuckGo for answers.\n"
            "  Type 'help' to see all commands."
        )


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def list_movies() -> None:
    movies = _load_json(MOVIES_FILE)
    if not movies:
        print("  No movies in catalog.")
        return
    print("\n  🎬  Movies in catalog:\n")
    for m in movies:
        yr = m.get("year") or "—"
        print(f"    • {m['title']} ({yr})")
    print()


def run_session(title: str) -> None:
    all_facts = _load_json(FACTS_FILE)

    # Case-insensitive title match
    matched_key = next(
        (k for k in all_facts if k.lower() == title.lower()), None
    )
    facts = all_facts.get(matched_key, []) if matched_key else []

    print(BANNER)
    print(f"  🎬  Now watching: {title}")
    if facts:
        print(f"  I have {len(facts)} fun fact(s) ready — I'll share them as you watch!")
    else:
        print("  No pre-loaded facts for this title, but ask me anything!")
    print("\n  Type a question, 'help' for commands, or 'quit' to exit.\n")
    print("  " + "─" * 52)

    session = WatchSession(title, facts)
    session.start()
    try:
        while True:
            try:
                user_input = input("\n> ")
            except EOFError:
                break
            response = session.chat(user_input)
            if response == "QUIT":
                print("\n  👋  See you next time — enjoy the rest of the movie!")
                break
            if response:
                print(response)
    except KeyboardInterrupt:
        print("\n\n  👋  Watch session ended.")
    finally:
        session.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Theater Watch Buddy – your interactive AI movie companion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python watch_buddy.py "Cartoon Network VHS Tapes"\n'
            '  python watch_buddy.py "Felix the Cat: The Movie"\n'
            "  python watch_buddy.py --list\n"
        ),
    )
    parser.add_argument("title", nargs="?", help="Movie title to watch")
    parser.add_argument("--list", action="store_true", help="List available movies")
    args = parser.parse_args()

    if args.list:
        list_movies()
        return

    if not args.title:
        list_movies()
        parser.print_help()
        return

    run_session(args.title)


if __name__ == "__main__":
    main()
