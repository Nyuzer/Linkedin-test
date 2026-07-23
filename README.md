# LinkedIn Engagement Automation

A Python + Playwright automation that reads the LinkedIn home feed, likes the
most interesting posts, and drafts human-sounding comments with an AI assistant.

- **Level achieved:** Level 2 (Read & React + Comment Thoughtfully)
- **Actual time spent:** _<fill in — e.g. ~2h>_

---

## What it does

**Level 1 — Read and React**
Reuses a warmed Chrome profile, reads the home feed, likes the top *N*
interesting posts, and prints author + first 200 chars + outcome for each.

**Level 2 — Comment Thoughtfully**
Picks the 2–3 most substantial of those posts and drafts an authentic,
human-sounding comment for each with the Anthropic (Claude) API. Drafts are
printed, **never posted** (per the assignment).

---

## Requirements

- **Python 3.10+**
- **Google Chrome** installed (the automation drives your real Chrome; it falls
  back to Playwright's bundled Chromium if Chrome isn't found)
- A LinkedIn account
- *(Level 2 only)* an Anthropic API key

---

## Setup

```bash
# 1. (recommended) create a virtual environment
python -m venv venv
venv\Scripts\Activate.ps1            # Windows PowerShell
# source venv/bin/activate           # macOS/Linux

# 2. install dependencies + the browser
pip install -r requirements.txt
playwright install chromium

# 3. one-time: log in and warm the Chrome profile
python save_login.py
#    -> a Chrome window opens. Log in to LinkedIn by hand (do any 2FA/captcha),
#       SCROLL the feed and open a couple of posts, then press Enter in the
#       terminal. Your session is saved in ./chrome-profile/ and reused.

# 4. (optional, for Level 2) configure the AI key
copy .env.example .env               # Windows   (cp on macOS/Linux)
#    -> edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Run

```bash
# safe first run — reads the feed and drafts comments, but does NOT like anything
python main.py --dry-run

# real run — likes posts and drafts comments
python main.py --max-likes 5

# capture the run to a file for review (UTF-8; use --out, not PowerShell ">")
python main.py --max-likes 10 --out sample_output.txt
```

| Flag           | Default | Description                                        |
| -------------- | ------- | -------------------------------------------------- |
| `--max-likes`  | 10      | How many interesting posts to like                 |
| `--comments`   | 3       | How many comments to draft (Level 2)               |
| `--dry-run`    | off     | Read + draft, but don't actually like anything     |
| `--out FILE`   | —       | Also write the run to FILE in UTF-8                 |
| `--headless`   | off     | Run without a visible window (less reliable here)  |

### Expected output

```
LEVEL 1 — READ & REACT
[1] Jane Developer
    Spent the week migrating our background jobs from cron to a proper queue...
    -> liked
...
LEVEL 2 — DRAFT 3 THOUGHTFUL COMMENTS (not posted)
[3] Jane Developer  (picked: 1274 chars)
    Post: Spent the week migrating our background jobs...
    Draft comment: We hit the same thing — half our "split the service" debates
    evaporated once we could actually see where time went...
Done.
```

---

## Troubleshooting

- **"Feed didn't load (no posts found)"** — LinkedIn is likely showing a
  checkpoint/captcha. Solve it in the open browser, or re-run `python save_login.py`
  and make sure real posts are visible before pressing Enter.
- **Several likes show `failed (TimeoutError)`** — LinkedIn throttles automation
  after a few quick likes. Lower `--max-likes`, and rerun later. This is expected;
  see Obstacles.
- **`AI unavailable (...)` in a draft** — a transient Anthropic API error (e.g.
  529 Overloaded). The run still completes; rerun to get a real draft.
- **Garbled non-ASCII in a saved file** — you used PowerShell `>` (UTF-16). Use
  `--out FILE` instead, which writes UTF-8.

---

## Design decisions

- **Persistent real-Chrome profile, not automated login.** `save_login.py` opens
  your real Chrome (`channel="chrome"`) with a persistent on-disk profile
  (`chrome-profile/`). You log in and scroll once by hand; `main.py` reuses it.
  This avoids automating the login form (the most bot-watched step), stores no
  password, and is what makes LinkedIn actually render the feed (see Obstacles).
- **Anti-automation launch flags.** `--disable-blink-features=AutomationControlled`
  hides the main automation fingerprint; `chromium_sandbox=True` avoids the
  `--no-sandbox` banner. Headed by default (headless is easily detected).
- **Class-independent selectors.** LinkedIn ships the feed with hashed CSS class
  names and no `data-urn`, so we anchor on the accessibility attributes it must
  keep for screen readers: the "Open control menu for post by *NAME*" button
  (author), the "Reaction button state" button (Like), and the post card as the
  nearest ancestor of both.
- **Body text parsing.** The body has no stable element, so we read the card's
  full text and parse the body out of it (after the "*time* •" marker or
  "Promoted"), then strip footer noise.
- **Resilience.** Retries + graceful fallbacks on both liking (LinkedIn throttling)
  and comment drafting (transient API errors), so one flaky call never crashes a run.
- **Human-ish pacing + ad filtering**, and **sync Playwright** (a single
  sequential scrape — no concurrency to exploit).

---

## Obstacles encountered

1. **LinkedIn blocked the automation outright.** A fresh Playwright Chromium
   loaded the feed (logged in, correct title) but served an empty shell — no
   posts — plus reCAPTCHA Enterprise and PerimeterX frames. LinkedIn had
   detected the automated browser and withheld the feed.
2. **Fix: a warmed, persistent real-Chrome profile** with anti-automation flags.
   Logging in and browsing once by hand got the feed to render.
3. **Hashed CSS classes.** Even rendering, every class is a random hash and
   there's no `data-urn` — an anti-scraping measure. Solved by anchoring on ARIA
   attributes instead.
4. **No stable body element** — the body is parsed out of the card's text.
5. **Throttled likes.** LinkedIn makes the Like button non-actionable after a few
   quick likes; mitigated with slow pacing + retries, but not 100% avoidable.
6. **Likes are real** — use `--dry-run` to exercise everything without touching
   LinkedIn.

---

## Files

```
main.py            Orchestration: Level 1 + Level 2, CLI flags, UTF-8 output
save_login.py      One-time manual login + profile warm-up
linkedin/
  browser.py       Persistent real-Chrome launch config (the anti-bot core)
  models.py        Post dataclass
  feed.py          Feed reading, ARIA-based selectors, body parsing, liking
  comments.py      Anthropic-based comment drafting (with retry/fallback)
requirements.txt   Dependencies
.env.example       Config template (ANTHROPIC_API_KEY)
```
