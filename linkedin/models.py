"""Data model for a single feed post."""

from dataclasses import dataclass


@dataclass
class Post:
    """One post scraped from the LinkedIn home feed.

    `urn` is LinkedIn's stable activity id (urn:li:activity:...). We keep it so a
    post can be re-identified even if the feed re-orders while we work.
    """

    index: int          # position in the feed as we read it (0-based)
    author: str         # display name of the author
    text: str           # post body text (may be truncated by LinkedIn's "see more")
    urn: str            # LinkedIn activity URN, or "" if we couldn't read it

    def preview(self, n: int = 200) -> str:
        """First `n` characters of the post, single-lined for clean printing."""
        flat = " ".join(self.text.split())
        return flat[:n]
