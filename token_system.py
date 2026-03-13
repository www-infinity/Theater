#!/usr/bin/env python3
"""
C13B0 Token System – 4-Hash Architecture

Creates and verifies research tokens where each token contains four
independent hashes so the article, sources, combined research package,
and token metadata can each be verified independently.

Usage:
    python token_system.py create --id 1054 --value 2593 --type Research \\
        --article article.md --sources sources.txt
    python token_system.py verify --id 1054
    python token_system.py list
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone

TOKENS_DIR = "tokens"
LEDGER_FILE = os.path.join("ledger", "treasury.json")

TOKEN_TYPE_EMOJIS = {
    "Research": "🧱",
    "Discovery": "⭐",
    "Economic": "💲",
    "Science": "🧬",
    "Machine": "⚙️",
    "Archive": "📜",
}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _token_dir(token_id: int) -> str:
    return os.path.join(TOKENS_DIR, f"token_{token_id}")


def _load_ledger() -> list:
    if not os.path.exists(LEDGER_FILE):
        return []
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_ledger(entries: list) -> None:
    os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def cmd_create(args: argparse.Namespace) -> None:
    token_dir = _token_dir(args.id)
    os.makedirs(token_dir, exist_ok=True)

    # --- write article ---
    if args.article and os.path.exists(args.article):
        with open(args.article, "r", encoding="utf-8") as f:
            article_text = f.read()
    else:
        article_text = args.article_text or ""

    article_path = os.path.join(token_dir, "article.md")
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(article_text)

    # --- write sources ---
    if args.sources and os.path.exists(args.sources):
        with open(args.sources, "r", encoding="utf-8") as f:
            sources_text = f.read()
    else:
        sources_text = args.sources_text or ""

    sources_path = os.path.join(token_dir, "sources.txt")
    with open(sources_path, "w", encoding="utf-8") as f:
        f.write(sources_text)

    # --- write metadata ---
    token_date = args.date or date.today().isoformat()
    metadata = {
        "id": args.id,
        "value": args.value,
        "type": args.type,
        "emoji": TOKEN_TYPE_EMOJIS.get(args.type, "🧱"),
        "date": token_date,
    }
    metadata_path = os.path.join(token_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # --- generate 4 hashes ---
    hash1_article = _sha256_file(article_path)
    hash2_sources = _sha256_file(sources_path)

    combined_text = article_text + sources_text
    hash3_combined = _sha256_text(combined_text)

    metadata_text = json.dumps(metadata, sort_keys=True)
    hash4_metadata = _sha256_text(metadata_text)

    hashes = {
        "HASH1_ARTICLE": hash1_article,
        "HASH2_SOURCES": hash2_sources,
        "HASH3_RESEARCH_PACKAGE": hash3_combined,
        "HASH4_TOKEN_METADATA": hash4_metadata,
    }
    hashes_path = os.path.join(token_dir, "hashes.json")
    with open(hashes_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)

    # --- update ledger ---
    entries = _load_ledger()
    entry = {
        "id": args.id,
        "value": args.value,
        "type": args.type,
        "emoji": metadata["emoji"],
        "date": token_date,
        "HASH4_TOKEN_METADATA": hash4_metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    entries = [e for e in entries if e.get("id") != args.id]
    entries.append(entry)
    _save_ledger(entries)

    emoji = metadata["emoji"]
    print(f"""
{emoji}{emoji}{emoji} TOKEN CREATED

ID:    {args.id}
Value: {args.value}
Type:  {args.type}
Date:  {token_date}

HASH1_ARTICLE:
  {hash1_article}

HASH2_SOURCES:
  {hash2_sources}

HASH3_RESEARCH_PACKAGE:
  {hash3_combined}

HASH4_TOKEN_METADATA:
  {hash4_metadata}

Stored in: {token_dir}/
""")


def cmd_verify(args: argparse.Namespace) -> None:
    token_dir = _token_dir(args.id)
    if not os.path.isdir(token_dir):
        print(f"Token {args.id} not found in {TOKENS_DIR}/", file=sys.stderr)
        sys.exit(1)

    article_path = os.path.join(token_dir, "article.md")
    sources_path = os.path.join(token_dir, "sources.txt")
    metadata_path = os.path.join(token_dir, "metadata.json")
    hashes_path = os.path.join(token_dir, "hashes.json")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open(hashes_path, "r", encoding="utf-8") as f:
        stored_hashes = json.load(f)
    with open(article_path, "r", encoding="utf-8") as f:
        article_text = f.read()
    with open(sources_path, "r", encoding="utf-8") as f:
        sources_text = f.read()

    current_hashes = {
        "HASH1_ARTICLE": _sha256_file(article_path),
        "HASH2_SOURCES": _sha256_file(sources_path),
        "HASH3_RESEARCH_PACKAGE": _sha256_text(article_text + sources_text),
        "HASH4_TOKEN_METADATA": _sha256_text(json.dumps(metadata, sort_keys=True)),
    }

    all_ok = True
    results = []
    for key in ("HASH1_ARTICLE", "HASH2_SOURCES", "HASH3_RESEARCH_PACKAGE", "HASH4_TOKEN_METADATA"):
        ok = current_hashes[key] == stored_hashes.get(key)
        status = "✅ OK" if ok else "❌ MISMATCH"
        results.append(f"  {key}: {status}")
        if not ok:
            all_ok = False

    emoji = metadata.get("emoji", "🧱")
    print(f"\n{emoji}{emoji}{emoji} TOKEN {args.id} VERIFICATION\n")
    for r in results:
        print(r)
    print()
    if all_ok:
        print("✅ All hashes verified — token is intact.\n")
    else:
        print("❌ Verification failed — token data has been modified.\n")
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:  # noqa: ARG001
    entries = _load_ledger()
    if not entries:
        print("Ledger is empty.")
        return
    print("\nToken Treasury Ledger\n" + "=" * 40)
    for e in sorted(entries, key=lambda x: x["id"]):
        emoji = e.get("emoji", "🧱")
        print(
            f"{emoji} Token {e['id']:>6}  "
            f"💲 {e['value']:>8}  "
            f"⭐ {e['type']:<12}  "
            f"📅 {e['date']}  "
            f"HASH4 {e['HASH4_TOKEN_METADATA'][:8]}..."
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="C13B0 Token System – 4-Hash Architecture"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = sub.add_parser("create", help="Create a new token")
    p_create.add_argument("--id", type=int, required=True, help="Token ID")
    p_create.add_argument("--value", type=int, required=True, help="Token value")
    p_create.add_argument("--type", required=True, choices=list(TOKEN_TYPE_EMOJIS.keys()), help="Token type")
    p_create.add_argument("--article", default="", help="Path to article file (or use --article-text)")
    p_create.add_argument("--article-text", dest="article_text", default="", help="Inline article text")
    p_create.add_argument("--sources", default="", help="Path to sources file (or use --sources-text)")
    p_create.add_argument("--sources-text", dest="sources_text", default="", help="Inline sources text")
    p_create.add_argument("--date", default="", help="Token date (YYYY-MM-DD, defaults to today)")

    # verify
    p_verify = sub.add_parser("verify", help="Verify a token's hashes")
    p_verify.add_argument("--id", type=int, required=True, help="Token ID")

    # list
    sub.add_parser("list", help="List all tokens in the ledger")

    args = parser.parse_args()
    if args.command == "create":
        cmd_create(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
