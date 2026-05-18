"""Validation agent: fact-check via RAG + web search, safety, moral, and human review.

Uses ChromaDB RAG (free, local) to cross-reference stories against actual
mythology source texts. DuckDuckGo search as supplementary check.
Human-in-the-loop approval before publishing (first N videos).
"""

import json
import re
import ollama
from duckduckgo_search import DDGS
from shared.logger import setup_logger
from shared.rag_store import query as rag_query
from config.settings import VALIDATION_MODEL

logger = setup_logger("validator")

# Set to 0 to skip human review (after you trust the pipeline)
HUMAN_REVIEW_FIRST_N = 30


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "parse_failed", "raw": text[:200]}


def _check_accuracy(story: dict) -> dict:
    """Check mythological accuracy via RAG (primary) + web search (secondary)."""

    # PRIMARY: RAG against actual source texts (ChromaDB)
    rag_context = rag_query(
        f"{story['title']} {' '.join(story.get('characters', []))} {story.get('source', '')}",
        n_results=5
    )

    # SECONDARY: Web search for additional cross-reference
    web_context = ""
    try:
        ddgs = DDGS()
        results = ddgs.text(
            f"{story['title']} {story.get('source', '')} Hindu mythology", max_results=3
        )
        web_context = "\n".join([r.get("body", "") for r in results])
    except Exception as e:
        logger.warning(f"Web search failed (non-critical): {e}")

    resp = ollama.chat(model=VALIDATION_MODEL, messages=[{
        "role": "user",
        "content": f"""Cross-reference this children's story against the original source texts and web sources.

STORY TITLE: {story['title']}
SOURCE TEXT: {story.get('source', 'unknown')}
CHARACTERS: {story.get('characters', [])}
STORY: {story['full_story'][:2000]}

ORIGINAL SOURCE TEXT PASSAGES (from RAG):
{rag_context[:2000]}

WEB REFERENCES:
{web_context[:1000]}

Check: Are characters from the correct source? Is the plot faithful to the original? Are relationships accurate?
Reply JSON only: {{"accurate": true/false, "issues": ["..."]}}"""
    }], options={"temperature": 0.1})

    return _parse_json(resp["message"]["content"])


def _check_safety(story: dict) -> dict:
    """Check content is safe for kids aged 4-10."""
    resp = ollama.chat(model=VALIDATION_MODEL, messages=[{
        "role": "user",
        "content": f"""Review this story for child safety (ages 4-10):

{story['full_story'][:3000]}

Check for: violence, gore, adult themes, scary demons, caste issues, complex philosophy.
Reply JSON only: {{"safe": true/false, "issues": ["..."]}}"""
    }], options={"temperature": 0.1})

    return _parse_json(resp["message"]["content"])


def _check_moral(story: dict) -> dict:
    """Validate the moral matches the story and is kid-appropriate."""
    resp = ollama.chat(model=VALIDATION_MODEL, messages=[{
        "role": "user",
        "content": f"""Validate the moral of this children's story:

STORY: {story['full_story'][:2000]}
STATED MORAL: {story['moral']}

Check: Does moral follow from story? Is it positive and age-appropriate?
Reply JSON only: {{"valid": true/false, "suggested_moral": "..."}}"""
    }], options={"temperature": 0.1})

    return _parse_json(resp["message"]["content"])


def _human_review(story: dict, result: dict) -> bool:
    """CLI-based human review. Returns True if approved."""
    print("\n" + "=" * 60)
    print(f"📖 HUMAN REVIEW: {story['title']}")
    print(f"   Source: {story.get('source', 'unknown')}")
    print(f"   Moral: {story['moral']}")
    print(f"   AI Checks: accuracy={result['accuracy'].get('accurate')}, "
          f"safety={result['safety'].get('safe')}, "
          f"moral={result['moral'].get('valid')}")

    if result['accuracy'].get('issues'):
        print(f"   ⚠ Accuracy issues: {result['accuracy']['issues']}")
    if result['safety'].get('issues'):
        print(f"   ⚠ Safety issues: {result['safety']['issues']}")

    print(f"\n   Story preview: {story['full_story'][:300]}...")
    print("=" * 60)

    while True:
        choice = input("\n   Approve? [y]es / [n]o / [s]kip review: ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        elif choice in ("s", "skip"):
            return True  # Trust AI checks
        print("   Enter y, n, or s")


def validate_story(story: dict, story_number: int = 0) -> dict:
    """Run validation: RAG + web accuracy, safety, moral, optional human review."""
    logger.info(f"  Validating: {story['title']}")

    accuracy = _check_accuracy(story)
    safety = _check_safety(story)
    moral = _check_moral(story)

    ai_approved = (
        accuracy.get("accurate", False) and
        safety.get("safe", False) and
        moral.get("valid", False)
    )

    result = {
        "approved": ai_approved,
        "accuracy": accuracy,
        "safety": safety,
        "moral": moral,
        "human_reviewed": False,
        "reason": "" if ai_approved else "Failed checks: " + ", ".join(
            [k for k, v in [("accuracy", accuracy.get("accurate")),
                            ("safety", safety.get("safe")),
                            ("moral", moral.get("valid"))] if not v]
        )
    }

    logger.info(f"  AI result: {'✓ PASSED' if ai_approved else '✗ FAILED'}")

    # Human review for first N stories (builds trust in the pipeline)
    if story_number < HUMAN_REVIEW_FIRST_N:
        human_ok = _human_review(story, result)
        result["human_reviewed"] = True
        result["approved"] = human_ok
        logger.info(f"  Human: {'✓ APPROVED' if human_ok else '✗ REJECTED'}")
    else:
        # After N stories, trust AI checks only
        result["approved"] = ai_approved

    return result
