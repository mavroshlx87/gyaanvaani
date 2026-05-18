# Ramayana Kids Stories - AI Video Generation Pipeline

**Automated YouTube & Instagram Channel** for kid-friendly Ramayana stories with beautiful animation, narration, subtitles, and moral lessons.

**Target Audience**: Children aged 4-15  
**Language**: English + Hindi (multilingual support)  
**Video Length**: 3-8 minutes  
**Goal**: 100–200 high-quality videos

---

## 🎯 Project Overview

This pipeline automatically generates complete animated storytelling videos based on the **Ramayana**. Each video includes:

- Engaging animated visuals (high-quality open-source models)
- Warm storytelling narration
- English + Hindi subtitles
- Clear "Moral of the Story" at the end
- SEO-optimized titles, descriptions & thumbnails

All built with **open-source tools** to keep running costs near zero (only electricity/hardware).

---

## ✨ Features

- Fully local / open-source stack
- Cultural accuracy through RAG + verification
- Multilingual narration & subtitles (English + Hindi)
- Consistent character design (Rama, Sita, Hanuman, etc.)
- Human-in-the-loop verification
- Automatic upload to YouTube & Instagram
- Resumable, scalable, and production-ready workflow

---

## 🛠 Tech Stack (All Open Source)

| Component              | Tool / Model                          | Purpose |
|------------------------|---------------------------------------|--------|
| Orchestration          | LangGraph (or n8n)                    | Agentic workflow |
| LLM (Story & Script)   | Llama-3.1-70B / Qwen3-72B / Sarvam    | Generation & verification |
| Video Generation       | Wan2.2 / LTX-Video / Mochi-1          | Animation |
| Image/Keyframes        | Flux.1 / SD3.5                        | Consistent characters |
| TTS (Narration)        | XTTS-v2 + Indic-TTS / MeloTTS         | English + Hindi |
| Subtitles              | Whisper + FFmpeg                      | Auto subtitles |
| Orchestration UI       | Gradio / Streamlit                    | Human review dashboard |
| Storage                | Local + MinIO                         | Assets |
| Upload                 | yt-upload + Instagrapi                | YouTube & Instagram |

---

## 📋 Complete Workflow (Agentic)

1. **Story Selection**  
   Choose Ramayana episodes (pre-made list of 150+ episodes available).

2. **Story Generation**  
   LLM creates kid-friendly script + scene-by-scene visual prompts.

3. **Verification Agent**  
   RAG-based fact checking against Valmiki Ramayana + human approval.

4. **Script Refinement**  
   Breaks story into timed scenes with detailed animation prompts.

5. **Media Generation** (parallel)
   - Keyframe generation (Flux)
   - Video clips (Wan2.2 / LTX-Video)
   - Narration (XTTS)
   - Background music
   - Subtitles (English + Hindi)

6. **Quality Assurance**  
   Auto + Human review.

7. **Upload**  
   Auto post to YouTube & Instagram with optimized metadata.

---

## 📁 Project Structure

```bash
ramayana-kids-pipeline/
├── README.md
├── main.py                    # Entry point
├── langgraph_workflow.py      # Main agent graph
├── agents/
│   ├── generator.py
│   ├── verifier.py
│   ├── script_refiner.py
│   ├── media_generator.py
│   └── uploader.py
├── prompts/
│   ├── story_generation.txt
│   ├── verification.txt
│   └── video_prompt.txt
├── data/
│   ├── ramayana_episodes.csv
│   ├── verified_stories/
│   └── rag_sources/           # Valmiki texts, PDFs
├── outputs/
│   ├── videos/
│   ├── scripts/
│   └── thumbnails/
├── config/
│   └── settings.yaml
├── ComfyUI_workflows/         # Video generation workflows
├── requirements.txt
└── Dockerfile
