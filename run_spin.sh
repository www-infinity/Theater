#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# C13B0 Cart — Mario's Wheel Of Fortune · Spin Engine
# ═══════════════════════════════════════════════════════════════════════
#
# Usage:
#   ./run_spin.sh [--wallet WALLET_ID] [--skip-cooldown]
#
# What this does:
#   1. Generates entropy for the spin
#   2. Selects a wheel segment
#   3. Calls research_writer.py to create research article + token file
#   4. Updates wallet and ledger
#   5. Commits and pushes to repo (requires GHP_SECRET or git credentials)
#
# Safety:
#   This script NEVER mines cryptocurrency, holds wallets, performs
#   trading, or interacts with any financial markets.
#   All tokens represent: research work · system growth · symbolic energy.
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────
STAMP=$(date -u +"%Y%m%d_%H%M%S")
DATE_LABEL=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
SKIP_COOLDOWN=""

# ── Parse args ─────────────────────────────────────────────────────────
WALLET_ID=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wallet)        WALLET_ID="$2"; shift 2 ;;
    --skip-cooldown) SKIP_COOLDOWN="--skip-cooldown"; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── Wallet: auto-generate if not provided ──────────────────────────────
if [[ -z "$WALLET_ID" ]]; then
  # Use a persistent wallet file so the same user keeps their history
  WALLET_FILE=".wallet_id"
  if [[ -f "$WALLET_FILE" ]]; then
    WALLET_ID=$(cat "$WALLET_FILE")
  else
    WALLET_ID="w_$(date +%s%N | sha256sum | head -c 12)"
    echo "$WALLET_ID" > "$WALLET_FILE"
    echo "🆕 New wallet created: $WALLET_ID"
  fi
fi

echo "═══════════════════════════════════════════════════════════"
echo "🎡 Mario's Wheel Of Fortune — C13B0 Spin Engine"
echo "🕒 $DATE_LABEL"
echo "🎒 Wallet: $WALLET_ID"
echo "═══════════════════════════════════════════════════════════"

# ── Wheel segments (must match mario-wheel/config.json) ───────────────
SEGMENTS=(
  "Mushroom:Silver:1"
  "Super Star:Wraith:50"
  "100 Coins:Silver:2"
  "Fire Flower:Silver:3"
  "Koopa Shell:Silver:1"
  "Thunder:Gold:10"
  "Princess:Gold:20"
  "Bowser:Lose:0"
  "Yoshi:Gold:5"
  "Cape Leaf:Silver:2"
  "Grand Prize:Wraith:100"
  "1-Up:Gold:15"
)

# ── Generate entropy and pick segment ─────────────────────────────────
ENTROPY=$(awk 'BEGIN { srand(); printf "%.6f", rand() }')
N=${#SEGMENTS[@]}
IDX=$(awk -v n="$N" -v e="$ENTROPY" 'BEGIN { srand(e * 999983); print int(rand() * n) }')
CHOSEN="${SEGMENTS[$IDX]}"

IFS=':' read -r SEG_LABEL SEG_TIER SEG_VALUE <<< "$CHOSEN"

echo ""
echo "🎰 Spinning…"
echo ""
echo "   Entropy:  $ENTROPY"
echo "   Segment:  $SEG_LABEL"
echo "   Tier:     $SEG_TIER"
echo "   Value:    ×$SEG_VALUE"
echo ""

# ── Run the research writer ────────────────────────────────────────────
python3 research_writer.py \
  --segment "$SEG_LABEL" \
  --tier    "$SEG_TIER" \
  --value   "$SEG_VALUE" \
  --wallet  "$WALLET_ID" \
  --stamp   "$STAMP" \
  $SKIP_COOLDOWN

# ── Commit to repo using GHP_SECRET ───────────────────────────────────
if [[ -n "${GHP_SECRET:-}" ]]; then
  # Configure git with the GHP token when running in CI
  REMOTE_URL=$(git remote get-url origin)
  REPO_PATH="${REMOTE_URL#https://github.com/}"
  REPO_PATH="${REPO_PATH%.git}"
  git remote set-url origin "https://x-access-token:${GHP_SECRET}@github.com/${REPO_PATH}.git"
fi

# Stage and commit only the token/research/wallet/spin artefacts
git add \
  "tokens/hourly/token_${STAMP}.json" \
  "tokens/research/token_${STAMP}.md" \
  "research/article_${STAMP}.md" \
  "wallets/${WALLET_ID}.json" \
  "spins/last_${WALLET_ID}.json" \
  "ledger/treasury.json" \
  2>/dev/null || true

# Check if there is anything staged
if git diff --cached --quiet; then
  echo "ℹ️  Nothing to commit (possibly blocked by cooldown)."
  exit 0
fi

TIER_EMOJI="🥈"
[[ "$SEG_TIER" == "Gold"   ]] && TIER_EMOJI="🥇"
[[ "$SEG_TIER" == "Wraith" ]] && TIER_EMOJI="👻"

git commit -m "${TIER_EMOJI} Mario Wheel Spin Token ${STAMP}" \
  -m "Segment: ${SEG_LABEL} | Tier: ${SEG_TIER} | ×${SEG_VALUE}" \
  -m "Wallet: ${WALLET_ID}"

git push origin HEAD

echo ""
echo "✅ Token committed and pushed."
echo "   🧱 Spin Token Generated: token_${STAMP}"
echo "   🍄 Research Created:    research/article_${STAMP}.md"
echo "   ⭐ Wheel Spin complete!"
