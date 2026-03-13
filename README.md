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

## Movie catalog

Film entries are stored in [`catalog/movies.json`](catalog/movies.json).
Each entry lists the title, year, and one or more archive.org source links.

To add a new film, append an object to that array:

```json
{
  "title": "My Film",
  "year": 1990,
  "sources": [
    { "label": "1080p", "url": "https://archive.org/details/..." }
  ]
}
```

## Watch Buddy

An interactive AI companion that watches movies **with** you.

* Pops trivia facts at timed intervals during playback
* Answers any question by searching **DuckDuckGo** in real time
* No API key required

```bash
# Start a watch session
python watch_buddy.py "Cartoon Network VHS Tapes"
python watch_buddy.py "PT-03 Monster of Mexico"

# List available movies
python watch_buddy.py --list
```

While watching, you can type:

| Input | What happens |
|-------|--------------|
| Any question (or ends with `?`) | DuckDuckGo search |
| `search <topic>` | Explicit DuckDuckGo lookup |
| `facts` | List all pre-loaded facts for the movie |
| `time` | Show elapsed playback time |
| `help` | Show all commands |
| `quit` | End the session |

Facts are stored in [`catalog/facts.json`](catalog/facts.json) — add a new
key matching the movie title to load facts for any film.

## Audio Repair Tool

Fixes common audio problems in old or degraded recordings using FFmpeg.

**Requires:** [FFmpeg](https://ffmpeg.org/download.html) on your PATH.

```bash
# Fix audio directly from archive.org (downloads automatically)
python audio_repair.py https://archive.org/details/pt-03-Monster-of-Mexico

# Fix a local file
python audio_repair.py my_movie.mp4

# Extra boost for very quiet recordings
python audio_repair.py my_movie.mp4 --boost 12

# Audio-only output
python audio_repair.py my_movie.mp4 --audio-only

# Preview the FFmpeg command without running it
python audio_repair.py my_movie.mp4 --dry-run
```

The repair pipeline applies five stages in order:

| Stage | Filter | Purpose |
|-------|--------|---------|
| 1 | High-pass (≤ 80 Hz) | Remove low-frequency rumble / hum |
| 2 | Low-pass (≥ 10 kHz) | Soften high-frequency tape hiss |
| 3 | Dynamic compressor | Lift quiet passages, tame loud peaks |
| 4 | Loudness normalise | EBU R128 broadcast-standard levels |
| 5 | Volume boost (+6 dB) | Explicit amplification for very quiet sources |

## File layout

```
catalog/
  movies.json   — film catalog with archive.org links
  facts.json    — per-movie timed trivia facts
tokens/
  token_1054/
    article.md
    sources.txt
    metadata.json
    hashes.json
ledger/
  treasury.json
audio_repair.py — audio fix tool
watch_buddy.py  — interactive AI watch companion
token_system.py — C13B0 token system
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
