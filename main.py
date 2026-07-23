"""LinkedIn engagement automation — Level 1 (read + like) and Level 2 (draft comments).

Prerequisites:
  1. pip install -r requirements.txt  &&  playwright install chromium
  2. python save_login.py            # one-time: log in + warm the Chrome profile
  3. (optional) put ANTHROPIC_API_KEY in a .env file for Level 2

Usage:
  python main.py                     # like 10 posts, draft 3 comments
  python main.py --max-likes 5 --comments 2
  python main.py --dry-run           # read + draft, but DON'T actually like

Level 1: reuses the warmed Chrome profile, reads the feed, likes the top N
         interesting posts, and prints author + first 200 chars + outcome.
Level 2: picks the 2-3 most substantial of those posts and drafts a human-like
         comment for each with Claude. Comments are printed, NOT posted.
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from linkedin import browser, comments, feed
from linkedin.models import Post


class _Tee:
    """Write to several streams at once (console + a UTF-8 file)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass


def pick_for_comments(posts: list[Post], n: int) -> list[Post]:
    """Choose the `n` most substantial posts (longer body = more to react to)."""
    return sorted(posts, key=lambda p: len(p.text), reverse=True)[:n]


def run(max_likes: int, num_comments: int, dry_run: bool, headless: bool) -> None:
    if not os.path.isdir(browser.PROFILE_DIR):
        sys.exit("No Chrome profile yet. Run `python save_login.py` first to log in once.")

    with sync_playwright() as p:
        ctx = browser.launch_context(p, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print("Opening LinkedIn feed...")
        try:
            feed.open_feed(page)
        except PWTimeout:
            ctx.close()
            sys.exit(
                "Feed didn't load (no posts found). LinkedIn may be showing a "
                "checkpoint/captcha — open the browser, solve it, then re-run. "
                "If it persists, re-run `python save_login.py`."
            )

        print(f"Reading feed and selecting up to {max_likes} interesting posts...\n")
        collected = feed.collect_interesting_posts(page, limit=max_likes)
        if not collected:
            ctx.close()
            sys.exit("No interesting posts found — try again or check the selectors (see README).")

        # ---- Level 1: like + report ----
        print("=" * 70)
        print("LEVEL 1 — READ & REACT")
        print("=" * 70)
        liked_posts: list[Post] = []
        for post, card in collected:
            outcome = "skipped (dry-run)" if dry_run else feed.like(page, card)
            liked_posts.append(post)
            print(f"\n[{post.index + 1}] {post.author}")
            print(f"    {post.preview(200)}")
            print(f"    -> {outcome}")

        # ---- Level 2: draft comments ----
        print("\n" + "=" * 70)
        print(f"LEVEL 2 — DRAFT {num_comments} THOUGHTFUL COMMENTS (not posted)")
        print("=" * 70)
        client = comments.build_client()
        if client is None:
            print("\n(No ANTHROPIC_API_KEY set — using fallback drafts.)")

        for post in pick_for_comments(liked_posts, num_comments):
            draft = comments.draft_comment(post, client)
            print(f"\n[{post.index + 1}] {post.author}  (picked: {len(post.text)} chars)")
            print(f"    Post: {post.preview(160)}")
            print(f"    Draft comment: {draft}")

        print("\nDone.")
        ctx.close()


def main() -> None:
    # LinkedIn feeds are full of non-ASCII text (Ukrainian, emoji); make sure the
    # Windows console doesn't crash printing them.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    parser = argparse.ArgumentParser(description="LinkedIn engagement automation")
    parser.add_argument("--max-likes", type=int, default=10, help="posts to like (default 10)")
    parser.add_argument("--comments", type=int, default=3, help="comments to draft (default 3)")
    parser.add_argument("--dry-run", action="store_true", help="read + draft but don't like")
    parser.add_argument("--headless", action="store_true", help="run headless (less reliable on LinkedIn)")
    parser.add_argument("--out", metavar="FILE", help="also write the run to FILE (UTF-8)")
    args = parser.parse_args()

    out_file = None
    if args.out:
        # Write the file ourselves in UTF-8 — PowerShell's `>` uses UTF-16 and
        # mangles non-ASCII text, so we tee to a proper UTF-8 file instead.
        out_file = open(args.out, "w", encoding="utf-8")
        sys.stdout = _Tee(sys.stdout, out_file)

    try:
        run(
            max_likes=args.max_likes,
            num_comments=args.comments,
            dry_run=args.dry_run,
            headless=args.headless,
        )
    finally:
        if out_file:
            out_file.close()


if __name__ == "__main__":
    main()
