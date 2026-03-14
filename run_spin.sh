#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# C13B0 Cart — Mario's Wheel Of Fortune · Spin Engine
# ═══════════════════════════════════════════════════════════════════════
#
# Two-layer token system:
#   1. Spin → system token → treasury/queue/  (pending_release)
#   2. Hourly claim → moves token from queue → treasury/archive + wallet
#
# Token growth:
#   🌱 Seed → 🔬 Research → 🛠️ Prototype → 📚 Historical Record
#
# Usage:
#   ./run_spin.sh                          # spin only
#   ./run_spin.sh --claim                  # spin + claim queued token
#   ./run_spin.sh --wallet w_abc123
#   ./run_spin.sh --skip-cooldown          # for testing
#
# Safety: never mines crypto · never trades · never touches markets.
# All tokens represent research work · system growth · symbolic energy.
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

STAMP=$(date -u +"%Y%m%d_%H%M%S")
DATE_LABEL=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
SKIP_COOLDOWN=""
DO_CLAIM=false
WALLET_ID=""

# ── Parse args ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wallet)        WALLET_ID="$2"; shift 2 ;;
    --skip-cooldown) SKIP_COOLDOWN="--skip-cooldown"; shift ;;
    --claim)         DO_CLAIM=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── Wallet: persistent local ID ────────────────────────────────────────
WALLET_FILE=".wallet_id"
if [[ -z "$WALLET_ID" ]]; then
  if [[ -f "$WALLET_FILE" ]]; then
    WALLET_ID=$(cat "$WALLET_FILE")
  else
    WALLET_ID="w_$(dd if=/dev/urandom bs=6 count=1 2>/dev/null | sha256sum | head -c 12)"
    echo "$WALLET_ID" > "$WALLET_FILE"
    echo "🆕 New wallet created: $WALLET_ID"
  fi
fi

echo "═══════════════════════════════════════════════════════════"
echo "🎡 Mario's Wheel Of Fortune — C13B0 Spin Engine"
echo "🕒 $DATE_LABEL"
echo "🎒 Wallet: $WALLET_ID"
echo "═══════════════════════════════════════════════════════════"

# ── Wheel segments (mirrors mario-wheel/config.json) ───────────────────
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

# ── Generate entropy + pick segment ───────────────────────────────────
ENTROPY=$(od -An -N4 -tu4 < /dev/urandom | tr -d ' \n')
N=${#SEGMENTS[@]}
IDX=$(( ENTROPY % N ))
CHOSEN="${SEGMENTS[$IDX]}"
IFS=':' read -r SEG_LABEL SEG_TIER SEG_VALUE <<< "$CHOSEN"

echo ""
echo "🎰 Spinning…"
echo "   Entropy:  $ENTROPY"
echo "   Segment:  $SEG_LABEL  ($SEG_TIER · ×$SEG_VALUE)"
echo ""

# ── Game mechanic hints ────────────────────────────────────────────────
if [[ "$SEG_LABEL" == "Mushroom" ]]; then
  echo "🍄 Mushroom Boost activated! Your next 'user' token gets ×2 value:"
  echo "   python3 research_writer.py user --mushroom-boost --topic \"...\" --wallet \"$WALLET_ID\""
  echo ""
fi
if [[ "$SEG_TIER" == "Gold" ]]; then
  echo "⭐ Stars — Discovery token minted with trending boost!"
  echo ""
fi

# ── Mint spin token → treasury/queue/ ─────────────────────────────────
python3 research_writer.py spin \
  --segment "$SEG_LABEL" \
  --tier    "$SEG_TIER" \
  --value   "$SEG_VALUE" \
  --wallet  "$WALLET_ID" \
  --stamp   "$STAMP" \
  $SKIP_COOLDOWN

# ── Optionally claim next queued token (1/hr) ──────────────────────────
if [[ "$DO_CLAIM" == true ]]; then
  echo ""
  echo "⬇️  Claiming next queued token…"
  python3 research_writer.py claim \
    --wallet "$WALLET_ID" \
    $SKIP_COOLDOWN || true
fi

# ── Commit to repo using GHP_SECRET ───────────────────────────────────
if [[ -n "${GHP_SECRET:-}" ]]; then
  REMOTE_URL=$(git remote get-url origin)
  REPO_PATH="${REMOTE_URL#https://github.com/}"
  REPO_PATH="${REPO_PATH%.git}"
  git remote set-url origin "https://x-access-token:${GHP_SECRET}@github.com/${REPO_PATH}.git"
fi

git add \
  "treasury/queue/" \
  "treasury/archive/" \
  "research/articles/" \
  "tokens/user/" \
  "tokens/spins/" \
  "wallets/${WALLET_ID}.json" \
  "state/" \
  "ledger/treasury.json" \
  2>/dev/null || true

if git diff --cached --quiet; then
  echo "ℹ️  Nothing to commit."
  exit 0
fi

TIER_EMOJI="🥈"
[[ "$SEG_TIER" == "Gold"   ]] && TIER_EMOJI="🥇"
[[ "$SEG_TIER" == "Wraith" ]] && TIER_EMOJI="👻"
[[ "$SEG_TIER" == "Lose"   ]] && TIER_EMOJI="💀"

git commit \
  -m "${TIER_EMOJI} Mario Wheel Spin Token ${STAMP}" \
  -m "🧱 Spin Token Generated | 🍄 Research Created | ⭐ Wheel Spin" \
  -m "Segment: ${SEG_LABEL} | Tier: ${SEG_TIER} | ×${SEG_VALUE} | Wallet: ${WALLET_ID}"

git push origin HEAD

echo ""
echo "✅ Committed and pushed."
echo "   🧱 Spin Token Generated:  token_${STAMP}"
echo "   🍄 Research Created:      research/articles/article_${STAMP}.md"
echo "   ⭐ Wheel Spin complete!"
echo "   🏦 Token in treasury queue — claim with: ./run_spin.sh --claim"
