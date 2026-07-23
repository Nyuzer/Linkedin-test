"""Read the LinkedIn home feed and like posts.

LinkedIn hashes its CSS class names (e.g. `_66f66072`) and strips data-urn from
the feed, so class-based selectors don't work. Instead we anchor on the
accessibility attributes LinkedIn must keep for screen readers:

  - author     -> button[aria-label^="Open control menu for post by <NAME>"]
  - post card  -> nearest ancestor <div> of that button that also contains a
                  "Reaction button state" (Like) button
  - like       -> button[aria-label^="Reaction button state"]

The body text has no stable element, so we read the whole card's text and parse
the body out of it (it starts after the "<time> •" marker, or after "Promoted").
"""

import random
import re
import time

from playwright.sync_api import Locator, Page

from .browser import FEED_URL
from .models import Post

# A post needs at least this many characters of body text to be "interesting".
MIN_TEXT_LEN = 100

# --- Stable anchors -----------------------------------------------------------
CONTROL_PREFIX = "Open control menu for post by "
CONTROL_SEL = f"button[aria-label^='{CONTROL_PREFIX}']"
# From the control button, the post card is the nearest ancestor div that also
# holds a Like button — a structural anchor that survives class hashing.
POST_XPATH = "xpath=ancestor::div[.//button[starts-with(@aria-label,'Reaction button state')]][1]"
REACTION_SEL = "button[aria-label^='Reaction button state']"

# "<n><unit> • " time marker that sits right before the body (1d •, 5h •, 2w •, 3mo •).
_TIME_RE = re.compile(
    r"\b\d+\s*(?:s|m|h|d|w|mo|yr|second|minute|hour|day|week|month|year)s?\b\s*•\s*",
    re.IGNORECASE,
)
_LEADING_UI_RE = re.compile(r"^(Follow|Following|Subscribe)\s+", re.IGNORECASE)
# Footer noise that can leak into the body of short posts — cut the body here.
_FOOTER_RE = re.compile(
    r"(…\s*more\b"
    r"|\s+Like\s+Comment\s+(?:Repost\s+)?Send\b"
    r"|\s+\d[\d,]*\s+reactions?\b"
    r"|\s+\d[\d,]*\s+comments?\b"
    r"|Activate to view larger image)",
    re.IGNORECASE,
)


def _human_pause(lo: float = 1.0, hi: float = 2.5) -> None:
    time.sleep(random.uniform(lo, hi))


def extract_body(full_text: str) -> str:
    """Pull the post body out of a card's full inner_text."""
    t = " ".join((full_text or "").split())
    if t.startswith("Feed post "):
        t = t[len("Feed post "):]
    m = _TIME_RE.search(t)
    if m:
        body = t[m.end():]
    elif "Promoted " in t:
        body = t.split("Promoted ", 1)[1]
    else:
        body = t
    body = _LEADING_UI_RE.sub("", body)
    footer = _FOOTER_RE.search(body)
    if footer:
        body = body[:footer.start()]
    return body.strip()


def open_feed(page: Page) -> None:
    """Navigate to the feed and wait for the first post to appear."""
    page.goto(FEED_URL, wait_until="domcontentloaded")
    page.wait_for_selector(CONTROL_SEL, timeout=30_000)
    _human_pause()


def collect_interesting_posts(page: Page, limit: int) -> list[tuple[Post, Locator]]:
    """Scroll the feed and return up to `limit` interesting posts.

    Returns (Post, post-card locator) pairs. Skips promoted/ad posts and posts
    with too little text.
    """
    results: list[tuple[Post, Locator]] = []
    seen: set[str] = set()
    scrolls = 0

    while len(results) < limit and scrolls < 15:
        controls = page.locator(CONTROL_SEL)
        for i in range(controls.count()):
            if len(results) >= limit:
                break
            menu = controls.nth(i)
            label = menu.get_attribute("aria-label") or ""
            if not label.startswith(CONTROL_PREFIX):
                continue
            author = label[len(CONTROL_PREFIX):].strip()

            post = menu.locator(POST_XPATH)
            if post.count() == 0:
                continue

            full = post.inner_text()
            if " Promoted " in f" {full[:200]} ":   # skip ads
                continue
            body = extract_body(full)
            if not author or len(body) < MIN_TEXT_LEN:
                continue

            key = f"{author}:{body[:60]}"
            if key in seen:
                continue
            seen.add(key)
            results.append((Post(index=len(results), author=author, text=body, urn=""), post))

        if len(results) < limit:
            page.mouse.wheel(0, 2000)
            _human_pause(1.2, 2.2)
            scrolls += 1

    return results


def like(page: Page, post: Locator) -> str:
    """Click the Like button inside a post card. Returns a short outcome string.

    Slow, human-ish pacing and a longer timeout matter here: LinkedIn starts
    throttling (making the button non-actionable) after a few quick likes, so we
    bring the card into view, pause, click with a generous timeout, and retry once.
    """
    btn = post.locator(REACTION_SEL).first
    if btn.count() == 0:
        return "no like button found"
    label = (btn.get_attribute("aria-label") or "").lower()
    if "no reaction" not in label:
        return "already liked"

    last_exc = None
    for attempt in range(2):
        try:
            post.scroll_into_view_if_needed(timeout=5000)
            _human_pause(1.0, 2.0)
            btn.click(timeout=8000)          # Playwright auto-waits for actionable
            _human_pause(2.0, 3.5)           # slow down between likes (anti-throttle)
            return "liked"
        except Exception as exc:
            last_exc = exc
            _human_pause(1.5, 2.5)
    return f"failed ({last_exc.__class__.__name__})"
