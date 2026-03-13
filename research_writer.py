#!/usr/bin/env python3
"""
Mario's Wheel Of Fortune — Research Writer & Token Minter
==========================================================

Two-layer token system:

  Layer 1 — User Research Tokens
    User writes an article → Print Token → treasury/queue/
    Hourly release system moves it from queue → wallet

  Layer 2 — Spin (System) Tokens
    Wheel spin produces a system token → treasury/queue/
    Same hourly release rule applies

Token Growth Stages (One Token = One Project Seed):
  🌱 Seed        → Token printed, enters treasury queue
  🔬 Research    → Article or project attached; token claimed
  🛠️ Prototype   → Something built on the token
  📚 Archived    → Permanently stored in treasury library

Usage:
  # User research token
  python research_writer.py user --topic "AI Memory Systems" \\
      --body "..." --wallet w_abc123 --stamp 20260313_150000

  # Spin token
  python research_writer.py spin --segment "Mushroom" --tier Silver \\
      --value 1 --wallet w_abc123 --stamp 20260313_150000

  # Claim next token from queue (hourly release)
  python research_writer.py claim --wallet w_abc123

  # List treasury queue
  python research_writer.py queue

Safety:
  Never mines crypto · never holds real wallets · never trades markets.
  All tokens represent: research work · system growth · symbolic energy.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# ── Paths (mirrors index.html localStorage structure) ─────────────────
TREASURY_QUEUE   = os.path.join("treasury", "queue")
TREASURY_ARCHIVE = os.path.join("treasury", "archive")
TREASURY_PROJECTS = os.path.join("treasury", "projects")
TOKENS_USER      = os.path.join("tokens", "user")
TOKENS_SPINS     = os.path.join("tokens", "spins")
RESEARCH_ARTICLES = os.path.join("research", "articles")
WALLETS_DIR      = "wallets"
STATE_DIR        = "state"
LEDGER_FILE      = os.path.join("ledger", "treasury.json")

TIER_TO_TYPE = {
    "Silver": "Research",
    "Gold":   "Discovery",
    "Wraith": "Economic",
}
TYPE_EMOJI = {
    "Research":  "🧱",
    "Discovery": "⭐",
    "Economic":  "💲",
    "Archive":   "📜",
}

COOLDOWN_HOURS = 1


# ── Utilities ──────────────────────────────────────────────────────────

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ── Cooldown / state ───────────────────────────────────────────────────

def _state_file(wallet_id: str) -> str:
    return os.path.join(STATE_DIR, f"last_release_{wallet_id}.json")


def can_claim(wallet_id: str) -> tuple[bool, float]:
    """Return (can_claim, seconds_remaining)."""
    state = load_json(_state_file(wallet_id), {})
    last  = state.get("last_token_time", "")
    if not last:
        return True, 0.0
    last_dt   = datetime.fromisoformat(last.replace("Z", "+00:00"))
    elapsed   = (datetime.now(timezone.utc) - last_dt).total_seconds()
    remaining = max(0.0, COOLDOWN_HOURS * 3600 - elapsed)
    return remaining == 0, remaining


def record_claim(wallet_id: str) -> None:
    save_json(_state_file(wallet_id), {
        "wallet":          wallet_id,
        "last_token_time": datetime.now(timezone.utc).isoformat(),
    })


# ── Article builders ───────────────────────────────────────────────────

def _spin_article(seg: str, tier: str, value: int,
                  wallet_id: str, ts: str, token_id: str) -> str:
    return "\n".join([
        f"# Spin Research: {seg}",
        "",
        "| Field | Value |", "|-------|-------|",
        f"| Tier | {tier} |",
        f"| Multiplier | ×{value} |",
        f"| Token ID | {token_id} |",
        f"| Wallet | {wallet_id} |",
        f"| Generated | {ts} |",
        "| Source | Mario's Wheel Of Fortune — Spin |",
        "",
        "## Token as Project Seed",
        "",
        "This spin token is a **blank research grant** — a container for future work.",
        f"Segment: **{seg}**. Tier: **{tier}** (×{value} multiplier).",
        "",
        "## Growth Path",
        "1. 🌱 Seed — Token printed, enters treasury queue",
        "2. 🔬 Research — Article or project attached",
        "3. 🛠️ Prototype — Something built on this token",
        "4. 📚 Historical Record — Archived in treasury library",
        "",
        "## Integrity",
        "",
        "This system never mines crypto, holds wallets, or trades markets.",
        "All tokens represent: research work · system growth · symbolic energy.",
    ])


def _user_article(topic: str, body: str,
                  wallet_id: str, ts: str, token_id: str) -> str:
    return "\n".join([
        f"# {topic or 'Research Article'}",
        "",
        f"**Author Wallet:** {wallet_id}",
        f"**Token ID:** {token_id}",
        f"**Timestamp:** {ts}",
        "**Source:** Mario's Wheel Of Fortune — Research Writer",
        "",
        "---",
        "",
        body or "*(no content)*",
        "",
        "---",
        "",
        "## Token Philosophy",
        "",
        "One token = one project seed. Value comes from what grows out of it:",
        "",
        "```",
        "Token → Research Article → Prototype / App / Item → Historical Record",
        "```",
    ])


# ── Core mint function ─────────────────────────────────────────────────

def mint(
    token_type: str,   # "user_research" | "spin_token"
    wallet_id: str,
    stamp: str,
    *,
    topic: str = "",
    body: str = "",
    segment: str = "",
    tier: str = "Silver",
    value: int = 0,
) -> dict:
    ts       = datetime.now(timezone.utc).isoformat()
    token_id = f"token_{stamp}"

    if token_type == "spin_token":
        type_name   = TIER_TO_TYPE.get(tier, "Archive")
        emoji       = TYPE_EMOJI.get(type_name, "📜")
        art_title   = f"Spin: {segment}"
        article     = _spin_article(segment, tier, value, wallet_id, ts, token_id)
    else:
        type_name   = "Research"
        emoji       = TYPE_EMOJI["Research"]
        art_title   = topic or "User Research"
        article     = _user_article(topic, body, wallet_id, ts, token_id)

    sources = "\n".join([
        "https://pewpi-infinity.github.io/Theater/",
        "https://github.com/www-infinity/Theater",
        f"source:{token_type}",
        f"generated:{ts}",
    ])

    # Article preview (first non-header line)
    preview = " ".join(
        l.strip() for l in article.split("\n")
        if l.strip() and not l.startswith("#") and not l.startswith("|")
        and not l.startswith("-") and l.strip() != "---"
    )[:130]

    metadata = {
        "token_id":       token_id,
        "type":           token_type,
        "author_wallet":  wallet_id,
        "timestamp":      ts,
        "status":         "pending_release",
        "stage":          "seed",
        "token_type":     type_name,
        "emoji":          emoji,
        "article_title":  art_title,
        "article_preview": preview,
        "research_file":  os.path.join(RESEARCH_ARTICLES, f"article_{stamp}.md"),
        **({"segment": segment, "tier": tier, "value": value}
           if token_type == "spin_token" else {"topic": topic}),
    }

    # 4-hash architecture (matches token_system.py & index.html)
    h1 = sha256(article)
    h2 = sha256(sources)
    h3 = sha256(article + "\n" + sources)
    h4 = sha256(json.dumps(metadata, ensure_ascii=False))

    record = {
        **metadata,
        "hashes": {
            "HASH1_ARTICLE":          h1,
            "HASH2_SOURCES":          h2,
            "HASH3_RESEARCH_PACKAGE": h3,
            "HASH4_TOKEN_METADATA":   h4,
        },
        "article.md":  article,
        "sources.txt": sources,
    }

    # ── Write files ──────────────────────────────────────────────────

    # Research article
    write_text(metadata["research_file"], article)

    # Treasury queue entry
    save_json(os.path.join(TREASURY_QUEUE, f"{token_id}.json"), record)

    # Token type-specific file
    if token_type == "spin_token":
        save_json(os.path.join(TOKENS_SPINS, f"{token_id}.json"), record)
    else:
        save_json(os.path.join(TOKENS_USER, f"{token_id}.json"), record)

    # Update wallet
    _update_wallet(wallet_id, record)

    # Update ledger
    _append_ledger({
        "token_id":   token_id,
        "wallet":     wallet_id,
        "type":       type_name,
        "tier":       tier if token_type == "spin_token" else "n/a",
        "value":      value,
        "status":     "pending_release",
        "date":       ts[:10],
    })

    return record


def _update_wallet(wallet_id: str, record: dict) -> None:
    wf   = os.path.join(WALLETS_DIR, f"{wallet_id}.json")
    data = load_json(wf, None) or {
        "wallet":            wallet_id,
        "tokens":            [],
        "research_created":  0,
        "spins_total":       0,
        "last_updated":      None,
    }
    queue_ids = [
        t["token_id"] if isinstance(t, dict) else t
        for t in data.get("tokens", [])
    ]
    if record["token_id"] not in queue_ids:
        data["tokens"].append({
            "token_id": record["token_id"],
            "type":     record["type"],
            "status":   "pending_release",
            "stage":    "seed",
        })
    if record["type"] == "user_research":
        data["research_created"] = data.get("research_created", 0) + 1
    else:
        data["spins_total"] = data.get("spins_total", 0) + 1
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_json(wf, data)


def _append_ledger(entry: dict) -> None:
    ledger = load_json(LEDGER_FILE, []) or []
    ledger.append(entry)
    save_json(LEDGER_FILE, ledger)


# ── Claim (hourly release) ─────────────────────────────────────────────

def claim(wallet_id: str, skip_cooldown: bool = False) -> dict | None:
    """Move oldest pending token from treasury/queue to treasury/archive."""

    if not skip_cooldown:
        ok, remaining = can_claim(wallet_id)
        if not ok:
            m, s = int(remaining // 60), int(remaining % 60)
            print(f"⏳ Cooldown active — next claim in {m}m {s:02d}s.")
            return None

    if not os.path.exists(TREASURY_QUEUE):
        print("ℹ️  Treasury queue directory does not exist.")
        return None

    queue_files = sorted(
        f for f in os.listdir(TREASURY_QUEUE)
        if f.endswith(".json") and f != ".gitkeep"
    )
    pending = []
    for fn in queue_files:
        data = load_json(os.path.join(TREASURY_QUEUE, fn))
        if isinstance(data, dict) and data.get("status") == "pending_release":
            if not data.get("author_wallet") or data["author_wallet"] == wallet_id:
                pending.append((fn, data))

    if not pending:
        print("ℹ️  No pending tokens in queue for this wallet.")
        return None

    fn, tok = pending[0]
    tok["status"] = "released"
    tok["stage"]  = "research"

    # Move to archive
    archive_path = os.path.join(TREASURY_ARCHIVE, fn)
    save_json(archive_path, tok)
    os.remove(os.path.join(TREASURY_QUEUE, fn))

    # Update wallet — mark as released
    wf   = os.path.join(WALLETS_DIR, f"{wallet_id}.json")
    data = load_json(wf, {})
    for t in data.get("tokens", []):
        if isinstance(t, dict) and t.get("token_id") == tok["token_id"]:
            t["status"] = "released"
            t["stage"]  = "research"
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_json(wf, data)

    record_claim(wallet_id)
    return tok


# ── CLI ────────────────────────────────────────────────────────────────

def _stamp_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def cmd_user(args: argparse.Namespace) -> None:
    if not args.topic and not args.body:
        print("❌ Provide --topic and/or --body.")
        sys.exit(1)
    stamp  = args.stamp or _stamp_now()
    record = mint(
        "user_research", args.wallet, stamp,
        topic=args.topic or "", body=args.body or "",
    )
    print(f"🧱 User token minted:  {record['token_id']}")
    print(f"   Wallet:    {record['author_wallet']}")
    print(f"   Article:   {record['research_file']}")
    print(f"   Stage:     🌱 {record['stage']}")
    print(f"   Hash1:     {record['hashes']['HASH1_ARTICLE'][:16]}…")


def cmd_spin(args: argparse.Namespace) -> None:
    if args.value == 0:
        print("💀 Bowser — no token minted this spin.")
        sys.exit(0)
    stamp  = args.stamp or _stamp_now()
    record = mint(
        "spin_token", args.wallet, stamp,
        segment=args.segment, tier=args.tier, value=args.value,
    )
    print(f"🎰 Spin token minted:  {record['token_id']}")
    print(f"   Wallet:    {record['author_wallet']}")
    print(f"   Segment:   {record['segment']} (×{record['value']})")
    print(f"   Tier:      {record['tier']}")
    print(f"   Stage:     🌱 {record['stage']}")
    print(f"   Article:   {record['research_file']}")


def cmd_claim(args: argparse.Namespace) -> None:
    tok = claim(args.wallet, skip_cooldown=args.skip_cooldown)
    if tok:
        print(f"✅ Claimed:  {tok['token_id']}")
        print(f"   Stage:   🔬 research")
        print(f"   Archived: {os.path.join(TREASURY_ARCHIVE, tok['token_id'] + '.json')}")


def cmd_queue(args: argparse.Namespace) -> None:
    files = sorted(f for f in os.listdir(TREASURY_QUEUE) if f.endswith(".json"))
    if not files:
        print("Treasury queue is empty.")
        return
    print(f"Treasury queue ({len(files)} token(s)):")
    for fn in files:
        data = load_json(os.path.join(TREASURY_QUEUE, fn))
        print(f"  {data.get('emoji','?')} {data.get('token_id','?')}  "
              f"[{data.get('status','?')}]  {data.get('article_title','')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mario's Wheel Of Fortune — Research Writer & Token Minter"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # user
    p_user = sub.add_parser("user", help="Mint a user research token")
    p_user.add_argument("--topic",  default="", help="Article title / topic")
    p_user.add_argument("--body",   default="", help="Article body text")
    p_user.add_argument("--wallet", required=True, help="Wallet ID")
    p_user.add_argument("--stamp",  default="",  help="Timestamp stamp (auto if omitted)")

    # spin
    p_spin = sub.add_parser("spin", help="Mint a spin (system) token")
    p_spin.add_argument("--segment",  required=True)
    p_spin.add_argument("--tier",     required=True, choices=["Silver", "Gold", "Wraith", "Lose"])
    p_spin.add_argument("--value",    required=True, type=int)
    p_spin.add_argument("--wallet",   required=True)
    p_spin.add_argument("--stamp",    default="")

    # claim
    p_claim = sub.add_parser("claim", help="Release next queued token to wallet (1/hr)")
    p_claim.add_argument("--wallet",        required=True)
    p_claim.add_argument("--skip-cooldown", action="store_true")

    # queue
    sub.add_parser("queue", help="List treasury queue")

    args = parser.parse_args()
    {"user": cmd_user, "spin": cmd_spin, "claim": cmd_claim, "queue": cmd_queue}[args.cmd](args)


if __name__ == "__main__":
    main()
