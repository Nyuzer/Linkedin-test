"""Shared browser launch config.

We use a PERSISTENT profile with the real installed Chrome and an anti-automation
flag. LinkedIn hard-detects a fresh Chromium (navigator.webdriver, --no-sandbox)
and refuses to render the feed, so we warm a real profile once (save_login.py)
and reuse it. This is the single most important part of making LinkedIn work.
"""

PROFILE_DIR = "chrome-profile"          # persistent Chrome profile lives here
FEED_URL = "https://www.linkedin.com/feed/"


def launch_context(p, headless: bool = False):
    """Launch a persistent context. Real Chrome if available, else Chromium."""
    common = dict(
        user_data_dir=PROFILE_DIR,
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
        chromium_sandbox=True,          # keep sandbox -> no "--no-sandbox" banner
        no_viewport=True,               # use the real window size
        locale="en-US",
    )
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **common)
    except Exception:
        # Chrome channel not installed — fall back to Playwright's bundled Chromium.
        return p.chromium.launch_persistent_context(**common)
