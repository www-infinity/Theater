# Theater

C13B0 Token System – 4-Hash Architecture.

## Purpose

Each token represents a research output and its supporting evidence.
Four independent hashes are stored per token so the **article**, **sources**,
**combined research package**, and **token metadata** can all be verified
independently. This prevents corruption, manipulation, or broken references.

## Token types

| Emoji | Type     |
|-------|----------|
| 🧱    | Research |
| ⭐    | Discovery |
| 💲    | Economic |
| 🧬    | Science  |
| ⚙️    | Machine  |
| 📜    | Archive  |

## The 4-Hash model

| Hash | Covers |
|------|--------|
| HASH1_ARTICLE | research article (`article.md`) |
| HASH2_SOURCES | source list (`sources.txt`) |
| HASH3_RESEARCH_PACKAGE | article + sources combined |
| HASH4_TOKEN_METADATA | token identity (id, value, type, date) |

## File layout

```
tokens/
  token_1054/
    article.md
    sources.txt
    metadata.json
    hashes.json
ledger/
  treasury.json
token_system.py
```

## Quick start

```bash
# create a token
python token_system.py create \
  --id 1054 \
  --value 2593 \
  --type Research \
  --article-text "My research article…" \
  --sources-text "https://example.com/source1"

# verify a token
python token_system.py verify --id 1054

# list all tokens
python token_system.py list
```

## Token record example

```
🧱🧱🧱 TOKEN

ID:    1054
Value: 2593
Type:  Research
Date:  2026-03-13

HASH1_ARTICLE:
  e4d1a7...

HASH2_SOURCES:
  4ab12c...

HASH3_RESEARCH_PACKAGE:
  9f87ab...

HASH4_TOKEN_METADATA:
  6bd21f...
```
