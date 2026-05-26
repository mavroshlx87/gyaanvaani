# 🎬 Mythological Stories — AI Video Pipeline

Automated pipeline to generate animated kids videos from Indian mythology and publish to YouTube & Instagram Reels. 100% open-source, near-zero cost.

**Target Audience:** Children aged 4-10
**Output:** YouTube (7-8 min, 16:9) + Instagram Reels (60 sec, 9:16)
**Hardware:** MacBook 16GB RAM
**Cost:** ~$5-10 for 100 videos

---

## Pipeline Flow

```mermaid
flowchart TD
    subgraph SETUP["⚙️ One-Time Setup"]
        S1["Install Ollama + Qwen3:8b"]
        S2["Download source texts<br/><code>python data/download_sources.py</code>"]
        S3["Build RAG index<br/><code>python -m shared.rag_store</code>"]
        S1 --> S2 --> S3
    end

    subgraph STAGE1["📖 Stage 1 — Story Generation"]
        A1["Load Qwen3:8b"] --> A2["Generate 100+ stories<br/>5 per batch × 2 batches × 12 sources"]
        A2 --> A3["Save as JSON files<br/>output/stories/pending/0001_title.json"]
        A3 --> A4["Dedup check<br/>skip existing titles"]
        A4 --> A5["Unload model · FREE RAM"]
    end

    subgraph STAGE2["🎨 Stage 2 — Validate + Produce (Daily)"]
        B1["Pick next file from<br/>pending/ folder"]
        B1 --> B2["Load Qwen3:8b"]

        B2 --> B3{"Validate<br/>RAG + Web + Safety"}
        B3 -->|FAIL| B3R["Move to rejected/"]
        B3 -->|PASS| B4{"Human Review<br/>(first 30 only)"}
        B4 -->|REJECT| B3R
        B4 -->|APPROVE| B5["Script 18 scenes"]
        B5 --> B6["Unload model · FREE RAM"]

        B6 --> B7["Generate 18 images<br/>FLUX.1 via Colab"]
        B7 --> B8["Generate narration<br/>Kokoro TTS · CPU"]
        B8 --> B9["Generate subtitles<br/>Faster-Whisper · CPU"]
        B9 --> B10["Assemble video<br/>MoviePy · Ken Burns"]
        B10 --> B11["Move to assembled/"]
    end

    subgraph STAGE3["📤 Stage 3 — Publish"]
        C1["Pick from assembled/"]
        C1 --> C2["Upload to YouTube<br/>madeForKids: true"]
        C1 --> C3["Upload to Instagram<br/>60s Reel · 9:16"]
        C2 --> C4["Move to published/"]
        C3 --> C4
    end

    SETUP --> STAGE1 --> STAGE2 --> STAGE3
```

### Story Status Flow (folder-based)

```
pending/ → validated/ → scripted/ → assembled/ → published/
              ↓
          rejected/
```

Status changes = file moves between folders. No database needed.

---

## Character Database & Lookup Engine (Plan A)

To ensure visual and voice consistency for characters across all generated scenes and videos:
- **Consistent Profiles**: We maintain structured character profile JSONs under `data/characters/`. Each profile details gender, ethnicity, timeline-based appearance/wardrobe/voice traits, and pre-formatted cinematic prompts (e.g., Pixar style).
- **Curated Database**: Pre-seeded with **73 core characters** (43 Ramayana + 30 Mahabharata) containing 91 timeline variants (e.g. child, exile, war) and 298 searchable aliases.
- **Dynamic Auto-Generation**: If a story mentions a character not yet in the database, the pipeline (`stage2/generators/scripter.py` via `shared/character_generator.py`) calls Ollama to auto-generate a profile JSON, saves it to `data/characters/auto_generated/`, and hot-registers it immediately.
- **Deduplication & Generic Filtering**: O(1) lookup checks prevent duplicate generation. Standard nouns (like *narrator, villagers, soldiers*) are automatically skipped.

Validate character data and lookups:
```bash
python3 data/characters/validate_characters.py
```

---

## Tech Stack

| Component | Tool | Cost |
|:--|:--|:--|
| LLM | Ollama + Qwen3:8b | $0 |
| RAG Fact-Check | ChromaDB + source texts | $0 |
| Web Search | DuckDuckGo (Python) | $0 |
| Character Store | Curated profiles + LLM Auto-generator | $0 |
| Image Gen | Google Colab free + FLUX.1-dev | $0 |
| TTS | Kokoro TTS (82M, CPU) | $0 |
| Subtitles | Faster-Whisper (CPU) | $0 |
| Video Assembly | MoviePy + FFmpeg | $0 |
| Music | Royalty-free downloads | $0 |
| Storage | JSON files (no database) | $0 |
| Orchestration | Python scripts + CRON | $0 |
| Publishing | YouTube/Instagram APIs | $0 |

---

## Quick Start

### 1. Install Prerequisites

```bash
# Ollama (local LLM runtime)
brew install ollama
ollama serve                   # Start server in background

# Pull models (~5GB each, one-time)
ollama pull qwen3:8b           # Creative writing, scripting, validation

# FFmpeg (video encoding)
brew install ffmpeg

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup RAG Knowledge Base

```bash
# Auto-download public domain mythology texts (Ramayana, Mahabharata, etc.)
python data/download_sources.py

# Index into ChromaDB vector store (one-time, ~1 min)
python -m shared.rag_store
```

### 3. Run Stage 1 — Generate Stories

```bash
python stage1/generate_stories.py
```

- Generates 100+ stories across 12 mythology source sections
- 5 stories per LLM call × 2 batches × 12 sources = ~120 stories
- Each story saved as JSON file in `output/stories/pending/`
- 3-layer deduplication prevents repeat stories
- Takes ~30-40 min on 16GB Mac (one-time)

**Output example:**
```
output/stories/pending/
├── 0001_hanumans_leap_to_the_sun.json
├── 0002_the_breaking_of_shivas_bow.json
├── 0003_sitas_garden_of_kindness.json
└── ...
```

**Each JSON file:**
```json
{
  "id": 1,
  "title": "Hanuman's Leap to the Sun",
  "source": "Ramayana - Bala Kanda",
  "characters": ["Hanuman", "Surya", "Indra"],
  "full_story": "Long ago, in a lush green forest... (800-1000 words)",
  "moral": "True strength comes with humility.",
  "tags": ["courage", "humility", "Hanuman"],
  "status": "pending"
}
```

### 4. Run Stage 2 — Process One Story

```bash
python stage2/main.py
```

Picks the first file from `pending/` and processes it through 6 steps:

| Step | Tool | RAM | What Happens |
|:--|:--|:--|:--|
| 1. Validate | Qwen3:8b + ChromaDB + DuckDuckGo | ~6GB | Fact-check, safety, moral, human review |
| 2. Script | Qwen3:8b | ~6GB | Break into 18 scenes with image prompts |
| 3. Images | Google Colab (external) | 0 | Generate 18 images via FLUX.1-dev |
| 4. Voice | Kokoro TTS | ~300MB | 8-min narration WAV |
| 5. Subtitles | Faster-Whisper | ~500MB | SRT file from narration |
| 6. Assemble | MoviePy + FFmpeg | ~1GB | Ken Burns video with audio + subs |

**File moves:** `pending/` → `validated/` → `scripted/` → `assembled/`

**RAM Management:** Model loads/unloads between steps. Only one heavy model in RAM at a time.

### 5. Run Stage 3 — Publish

```bash
python stage3/youtube_upload.py
python stage3/instagram_upload.py
```

### 6. Automate (Optional)

```bash
# Daily CRON: process + publish one story at 6 AM
crontab -e
0 6 * * * cd /path/to/project && .venv/bin/python stage2/main.py && .venv/bin/python stage3/youtube_upload.py
```

---

## Project Structure

```
├── README.md
├── requirements.txt
├── config/
│   └── settings.py              # Model names, paths, video specs
├── data/
│   ├── download_sources.py      # Auto-downloads public domain texts
│   ├── rag_sources/             # Downloaded mythology texts (TXT/PDF)
│   └── chroma_db/               # Auto-generated vector store
├── stage1/
│   └── generate_stories.py      # Bulk story generation (5/call × 2 batches)
├── stage2/
│   ├── main.py                  # Daily orchestrator (sequential, RAM-managed)
│   ├── agents/
│   │   └── validator.py         # RAG + web fact-check + safety + human review
│   ├── generators/
│   │   ├── scripter.py          # Scene breakdown + image prompts
│   │   ├── image_gen.py         # ComfyUI/Colab image generation
│   │   └── voice_gen.py         # Kokoro TTS narration
│   ├── assembly/
│   │   ├── video_builder.py     # Ken Burns + stitching
│   │   └── subtitles.py         # Faster-Whisper subtitle burn-in
│   └── templates/
│       ├── intro.png            # Channel intro card
│       └── moral_card.png       # "Moral of the story" end card
├── stage3/
│   ├── youtube_upload.py        # YouTube Data API v3
│   └── instagram_upload.py      # Instagram Graph API
├── shared/
│   ├── store.py                 # File-based JSON store (replaces SQLite)
│   ├── ollama_utils.py          # Load/unload model helpers
│   ├── rag_store.py             # ChromaDB RAG indexer + query
│   └── logger.py
├── output/
│   ├── stories/                 # Story JSON files by status
│   │   ├── pending/             # New, unprocessed stories
│   │   ├── validated/           # Passed all checks
│   │   ├── scripted/            # Scenes generated
│   │   ├── assembled/           # Video ready
│   │   ├── published/           # Live on YouTube/Instagram
│   │   └── rejected/            # Failed validation
│   └── media/                   # Generated assets per story
│       └── 0001_story_slug/
│           ├── images/          # Scene images (18 × 1920x1080)
│           ├── audio/           # narration.wav + subtitles.srt
│           └── video/           # final_youtube.mp4 + final_reel.mp4
└── assets/
    ├── music/                   # Royalty-free BGM files
    └── fonts/                   # Kid-friendly fonts for subtitles
```

---

## Deduplication (3-Layer)

Stories are never repeated, even across multiple runs:

| Layer | How | When |
|:--|:--|:--|
| 1. Load existing | Scan all status folders for title slugs | At startup |
| 2. Prompt injection | Pass existing titles in LLM prompt as "avoid these" | Per LLM call |
| 3. Insert check | Compare slug against known set before saving | Per story |

Safe to re-run `stage1/generate_stories.py` — only new unique stories get added.

---

## Stage Details

### Stage 1: Story Generation

**Run:** `python stage1/generate_stories.py`
**Model:** Qwen3:8b via Ollama (5 stories per call, 2 batches per source)
**Output:** ~120 JSON files in `output/stories/pending/`

Sources covered:
1. Ramayana — Bala, Ayodhya, Aranya, Sundara, Yuddha Kanda
2. Mahabharata — childhood stories, moral dilemmas
3. Bhagavata Purana — Krishna childhood
4. Panchatantra — Books 1-3
5. Hitopadesha — friendship and wisdom tales
6. Jataka Tales — animal fables

### Stage 2: Validation + Media Production

**Run:** `python stage2/main.py` (daily, processes 1 story)

#### Validation (4 checks)

| Check | Method | Fail Action |
|:--|:--|:--|
| Mythological accuracy | RAG against source texts + DuckDuckGo | Move to rejected/ |
| Content safety | LLM checks for violence, adult themes | Move to rejected/ |
| Moral validation | LLM verifies moral matches story | Suggest alternative |
| Human review | CLI prompt (first 30 stories only) | Move to rejected/ |

Set `HUMAN_REVIEW_FIRST_N = 0` in `stage2/agents/validator.py` to skip human review.

#### Scene Scripting

Breaks story into 18 scenes, each with:
- `narration_text` — narrator dialogue
- `image_prompt` — FLUX.1 prompt (always "3D Pixar style" prefix)
- `duration_seconds` — 20-30 sec per scene
- `camera_motion` — slow_zoom_in, slow_zoom_out, pan_left, pan_right

#### Image Generation

Uses Google Colab free tier with FLUX.1-dev (GGUF Q5) on T4 GPU.
18 images at 1920x1080 + 5 at 1080x1920 for Instagram.

#### Voice + Subtitles + Assembly

- **Kokoro TTS** — CPU-only, warm narrator voice, 0.9x speed
- **Faster-Whisper** — auto-generates SRT subtitles
- **MoviePy** — Ken Burns zoom/pan, crossfades, burned-in subs, intro/outro cards

### Stage 3: Publishing

- **YouTube** — Data API v3, `madeForKids: true` (COPPA required), SEO tags
- **Instagram** — Graph API, 60s reel, moral in caption

---

## RAM Management (16GB Mac)

Only one heavy model in RAM at any time. Sequential execution with explicit unloading.

```python
load_model("qwen3:8b")     # Load ~6GB
# ... validate + script ...
unload_all()                # Free RAM
# ... Kokoro TTS (300MB) ...
# ... Whisper (500MB) ...
# ... MoviePy (1GB) ...
```

See `shared/ollama_utils.py` for implementation.

---

## Cost Summary

| Item | Cost |
|:--|:--|
| All tools (local, open-source) | $0 |
| Electricity (~50 hrs compute) | ~$5 |
| VPS for CRON (optional) | $0-5/mo |
| **100 videos total** | **$5-10** |

---

## 6-Week Roadmap

| Week | Task |
|:--|:--|
| 1 | Install Ollama + Qwen3. Run Stage 1, generate 100 stories |
| 2 | Build validator agent with RAG + DuckDuckGo search |
| 3 | Set up Colab notebook for FLUX.1 images + Kokoro TTS |
| 4 | MoviePy assembly: Ken Burns, subtitles, intro/outro cards |
| 5 | YouTube + Instagram API integration |
| 6 | CRON automation, first 10 videos published |

---

## Future Upgrades

- Replace Kokoro → ElevenLabs for more expressive voices
- Replace Colab images → local GPU or Kling AI animated clips
- Add Wan2.2 for actual AI animation (instead of Ken Burns on stills)
- Add Hindi narration track for Indian audience
- Add thumbnail generation with click-bait text overlay
- Add Gradio/Streamlit dashboard for visual story review

---

## License

All tools used are open-source. Source texts are public domain (pre-1929 translations).
Content generated by the pipeline is original AI output.
Consult a lawyer regarding COPPA compliance before publishing kids content on YouTube.
