"""Draft human-sounding comments for selected posts using the Anthropic API.

Design notes:
- We only DRAFT comments here. Nothing is posted to LinkedIn (per the task).
- If ANTHROPIC_API_KEY is missing, build_client() returns None and we fall back
  to a simple templated draft so a demo run never crashes mid-way.
"""

import os
import time

from anthropic import Anthropic

from .models import Post

# Default model; override with ANTHROPIC_MODEL (e.g. claude-haiku-4-5).
# Read at call time (see _model()) so a value from a .env loaded in main() applies.
DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM = (
    "You write short, genuine LinkedIn comments as a working software engineer. "
    "Rules: one or two sentences; conversational; specific to the actual post; "
    "add one concrete thought, question, or shared experience. "
    "No emojis, no hashtags, no 'Great post!' filler, no corporate buzzwords, "
    "no restating the post back. Sound like a real person, not a brand."
)


def _model() -> str:
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)


def build_client() -> Anthropic | None:
    """Return an Anthropic client, or None if no API key is configured."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    # The SDK reads ANTHROPIC_API_KEY from the environment automatically.
    return Anthropic()


def _fallback(post: Post) -> str:
    """Deterministic draft used when no API key is available."""
    return (
        f"Interesting point, {post.author.split()[0]}. "
        "Curious how this played out in practice — did the trade-offs hold up?"
    )


def draft_comment(post: Post, client: Anthropic | None) -> str:
    """Draft a single human-sounding comment for `post`.

    Resilient to transient API errors (e.g. 529 Overloaded): retries a couple of
    times, then degrades to the template fallback so one flaky call never crashes
    the whole run.
    """
    if client is None:
        return _fallback(post)

    prompt = (
        f"Author: {post.author}\n\n"
        f"Post:\n{post.text}\n\n"
        "Write one authentic comment reacting to this post."
    )
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.messages.create(
                model=_model(),
                max_tokens=300,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        except Exception as exc:  # transient overload / rate limit / network
            last_exc = exc
            time.sleep(2 * (attempt + 1))

    name = last_exc.__class__.__name__ if last_exc else "error"
    return f"[AI unavailable ({name}) — re-run to retry] {_fallback(post)}"
