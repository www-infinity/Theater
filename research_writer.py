#!/usr/bin/env python3
"""
Mario's Wheel Of Fortune — Research Writer
==========================================

Generates a research article and mints a token file for each wheel spin.
Called by run_spin.sh (C13B0 cart integration).

Usage:
    python research_writer.py --segment "Mushroom" --tier Silver --value 1 \\
        --wallet w_abc123 --stamp 20260313_150000

Output:
    research/article_STAMP.md        ← research article
    tokens/hourly/token_STAMP.json   ← hourly token record
    tokens/research/token_STAMP.md   ← linked research record
    wallets/WALLET_ID.json           ← updated wallet
    spins/last_WALLET_ID.json        ← cooldown state

Safety:
    This tool NEVER mines cryptocurrency, holds wallets, performs
    trading, or interacts with any financial markets.
    All tokens represent: research work · system growth · symbolic energy.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# ── Paths ─────────────────────────────────────────────────────────────
RESEARCH_DIR  = "research"
TOKENS_HOURLY = os.path.join("tokens", "hourly")
TOKENS_RESEARCH = os.path.join("tokens", "research")
WALLETS_DIR   = "wallets"
SPINS_DIR     = "spins"
LEDGER_FILE   = os.path.join("ledger", "treasury.json")
CONFIG_FILE   = os.path.join("mario-wheel", "config.json")

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


# ── Helpers ───────────────────────────────────────────────────────────

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_json(path: str) -> dict | list:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict | list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ── Cooldown check ────────────────────────────────────────────────────

def check_cooldown(wallet_id: str, cooldown_hours: int = 1) -> tuple[bool, float]:
    """Return (can_spin, seconds_remaining)."""
    spin_file = os.path.join(SPINS_DIR, f"last_{wallet_id}.json")
    if not os.path.exists(spin_file):
        return True, 0.0
    state = load_json(spin_file)
    last  = state.get("last_spin_utc", "")
    if not last:
        return True, 0.0
    last_dt  = datetime.fromisoformat(last.replace("Z", "+00:00"))
    now_dt   = datetime.now(timezone.utc)
    elapsed  = (now_dt - last_dt).total_seconds()
    cooldown = cooldown_hours * 3600
    remaining = cooldown - elapsed
    return remaining <= 0, max(0.0, remaining)


def record_spin(wallet_id: str) -> None:
    spin_file = os.path.join(SPINS_DIR, f"last_{wallet_id}.json")
    save_json(spin_file, {
        "wallet": wallet_id,
        "last_spin_utc": datetime.now(timezone.utc).isoformat(),
    })


# ── Research article ──────────────────────────────────────────────────

def build_article(segment: str, tier: str, value: int,
                  wallet_id: str, stamp: str, ts: str) -> str:
    token_type = TIER_TO_TYPE.get(tier, "Archive")
    return "\n".join([
        f"# Spin Research Article: {segment}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Tier | {tier} |",
        f"| Multiplier | ×{value} |",
        f"| Token ID | token_{stamp} |",
        f"| Wallet | {wallet_id} |",
        f"| Generated | {ts} |",
        f"| Source | Mario's Wheel Of Fortune |",
        "",
        "## Research Notes",
        "",
        "This token represents a research spin on Mario's Wheel Of Fortune.",
        f"Segment landed: **{segment}**.",
        f"Prize tier: **{tier}** (×{value} multiplier).",
        "",
        "## Token Categories",
        "",
        "- 🥈 Silver tokens → Research (🧱) — foundational research work",
        "- 🥇 Gold tokens   → Discovery (⭐) — notable findings",
        "- 👻 Wraith tokens  → Economic (💲) — high-value insights",
        "",
        "## Integrity",
        "",
        "All tokens represent: research work · system growth · symbolic energy.",
        "No cryptocurrency is mined, held, or traded.",
    ])


def build_sources(ts: str) -> str:
    return "\n".join([
        "https://pewpi-infinity.github.io/Theater/",
        "https://github.com/www-infinity/Theater",
        "https://archive.org/details/supermarioworldcartoon",
        "source:Mario_Wheel_Spin",
        f"generated:{ts}",
    ])


# ── Wallet update ─────────────────────────────────────────────────────

def update_wallet(wallet_id: str, token_id: str) -> None:
    wallet_file = os.path.join(WALLETS_DIR, f"{wallet_id}.json")
    wallet = load_json(wallet_file) or {"wallet": wallet_id, "tokens": []}
    wallet.setdefault("tokens", [])
    if token_id not in wallet["tokens"]:
        wallet["tokens"].append(token_id)
    wallet["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_json(wallet_file, wallet)


# ── Ledger update ─────────────────────────────────────────────────────

def update_ledger(entry: dict) -> None:
    ledger = []
    if os.path.exists(LEDGER_FILE):
        ledger = load_json(LEDGER_FILE) or []
    ledger.append(entry)
    save_json(LEDGER_FILE, ledger)


# ── Main mint function ────────────────────────────────────────────────

def mint(segment: str, tier: str, value: int,
         wallet_id: str, stamp: str) -> dict:
    """Create all token artefacts and return the token record."""

    ts = datetime.now(timezone.utc).isoformat()

    # 1. Research article
    article_text  = build_article(segment, tier, value, wallet_id, stamp, ts)
    sources_text  = build_sources(ts)

    article_path  = os.path.join(RESEARCH_DIR, f"article_{stamp}.md")
    write_text(article_path, article_text)

    # 2. Metadata
    token_type = TIER_TO_TYPE.get(tier, "Archive")
    emoji      = TYPE_EMOJI.get(token_type, "📜")
    metadata   = {
        "token_id":      f"token_{stamp}",
        "wallet":        wallet_id,
        "spin_time":     ts,
        "token_type":    token_type,
        "emoji":         emoji,
        "tier":          tier,
        "value":         value,
        "segment":       segment,
        "date":          ts[:10],
        "source":        "Mario's Wheel Of Fortune",
        "research_file": article_path,
    }

    # 3. 4-Hash architecture (mirrors token_system.py)
    h1 = sha256_text(article_text)
    h2 = sha256_text(sources_text)
    h3 = sha256_text(article_text + "\n" + sources_text)
    h4 = sha256_text(json.dumps(metadata, ensure_ascii=False))

    hashes = {
        "HASH1_ARTICLE":          h1,
        "HASH2_SOURCES":          h2,
        "HASH3_RESEARCH_PACKAGE": h3,
        "HASH4_TOKEN_METADATA":   h4,
    }

    token_record = {
        **metadata,
        "hashes":       hashes,
        "article.md":   article_text,
        "sources.txt":  sources_text,
    }

    # 4. Write token files
    hourly_path   = os.path.join(TOKENS_HOURLY,   f"token_{stamp}.json")
    research_path = os.path.join(TOKENS_RESEARCH,  f"token_{stamp}.md")
    save_json(hourly_path, token_record)
    write_text(research_path, article_text)

    # 5. Update wallet + ledger
    update_wallet(wallet_id, f"token_{stamp}")
    update_ledger({
        "token_id": f"token_{stamp}",
        "wallet":   wallet_id,
        "type":     token_type,
        "value":    value,
        "tier":     tier,
        "date":     ts[:10],
    })

    return token_record


# ── CLI ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mario's Wheel Of Fortune — Research Writer & Token Minter"
    )
    parser.add_argument("--segment",  required=True, help="Wheel segment label, e.g. 'Mushroom'")
    parser.add_argument("--tier",     required=True,
                        choices=["Silver", "Gold", "Wraith", "Lose"],
                        help="Prize tier")
    parser.add_argument("--value",    required=True, type=int, help="Value multiplier")
    parser.add_argument("--wallet",   required=True, help="Wallet ID")
    parser.add_argument("--stamp",    required=True,
                        help="Timestamp stamp, e.g. 20260313_150000")
    parser.add_argument("--skip-cooldown", action="store_true",
                        help="Skip the 1-hour cooldown check (for testing)")
    args = parser.parse_args()

    if args.value == 0:
        print("💀 Bowser! No token minted this spin.")
        record_spin(args.wallet)
        sys.exit(0)

    if not args.skip_cooldown:
        can, remaining = check_cooldown(args.wallet)
        if not can:
            m = int(remaining // 60)
            s = int(remaining % 60)
            print(f"⏳ Cooldown active — next spin in {m}m {s:02d}s.")
            sys.exit(1)

    record = mint(
        segment=args.segment,
        tier=args.tier,
        value=args.value,
        wallet_id=args.wallet,
        stamp=args.stamp,
    )
    record_spin(args.wallet)

    print(f"✅ Token minted: {record['token_id']}")
    print(f"   Wallet:  {record['wallet']}")
    print(f"   Type:    {record['emoji']} {record['token_type']}")
    print(f"   Tier:    {record['tier']} ×{record['value']}")
    print(f"   Article: {record['research_file']}")
    print(f"   Hash1:   {record['hashes']['HASH1_ARTICLE'][:16]}…")


if __name__ == "__main__":
    main()
