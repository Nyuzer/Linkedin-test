"""One-time login + profile warm-up.

Run this once. A real Chrome window opens on LinkedIn. Log in by hand (including
any 2FA / captcha / checkpoint), then SCROLL the feed and look at a few posts so
the profile earns LinkedIn's trust. Everything is stored in the persistent
`chrome-profile/` directory, which main.py reuses — so it never automates the
login form (the step LinkedIn's anti-bot watches most closely) and the warmed
profile is far less likely to be blocked.

    python save_login.py
"""

from playwright.sync_api import sync_playwright

from linkedin.browser import FEED_URL, PROFILE_DIR, launch_context


def main() -> None:
    with sync_playwright() as p:
        ctx = launch_context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FEED_URL, wait_until="domcontentloaded")

        print("\n=== Manual login + warm-up ===")
        print("1. Log in to LinkedIn in the browser window (do any 2FA / captcha).")
        print("2. SCROLL the feed and open a couple of posts so the profile looks human.")
        print("3. When you can see real posts, return here and press Enter.\n")
        input("Press Enter once you're logged in and the feed shows posts... ")

        print(f"\nProfile saved in ./{PROFILE_DIR}/ — main.py will reuse it.")
        ctx.close()


if __name__ == "__main__":
    main()
