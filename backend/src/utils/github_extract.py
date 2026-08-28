"""
GitHub ingestion, honestly scoped: fetch ONE file's raw content from a
public GitHub repo (README, a doc, a source file) and ingest it as a
document. This is NOT a repo crawler, NOT a live-sync connector, and
doesn't index an entire codebase or its commit history -- see README for
why that's explicitly out of scope (real, separate connector work).

Accepts either:
- A github.com blob URL: https://github.com/owner/repo/blob/branch/path/to/file.py
- A raw.githubusercontent.com URL directly

Only these two hostnames are ever fetched from -- unlike website
ingestion, there's no arbitrary-host SSRF surface here since the target
is pinned to GitHub's own domains, not resolved from user input.
"""

import re

import httpx

from src.core.logging import logger

MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5MB cap -- this is source/doc files, not binaries
FETCH_TIMEOUT_SECONDS = 15

ALLOWED_HOSTS = {"github.com", "www.github.com", "raw.githubusercontent.com"}

_BLOB_URL_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+)$"
)


class GithubIngestionError(Exception):
    pass


def _to_raw_url(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        raise GithubIngestionError(
            "Only github.com or raw.githubusercontent.com URLs are supported."
        )

    if parsed.hostname == "raw.githubusercontent.com":
        return url

    match = _BLOB_URL_RE.match(url)
    if not match:
        raise GithubIngestionError(
            "Expected a GitHub file URL like "
            "https://github.com/owner/repo/blob/main/path/to/file.md"
        )

    return "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}".format(**match.groupdict())


def fetch_github_file(url: str) -> tuple[list[dict], str]:
    """Returns (pages, display_name) matching utils/pdf.py's page shape."""

    raw_url = _to_raw_url(url)

    try:
        with httpx.Client(follow_redirects=True, timeout=FETCH_TIMEOUT_SECONDS) as client:
            with client.stream("GET", raw_url) as response:
                if response.status_code == 404:
                    raise GithubIngestionError(
                        "That file wasn't found -- check the URL, branch name, and that the repo is public."
                    )
                response.raise_for_status()

                chunks = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_CONTENT_BYTES:
                        raise GithubIngestionError("That file is too large to ingest.")
                    chunks.append(chunk)
                raw_bytes = b"".join(chunks)

    except httpx.HTTPStatusError as e:
        raise GithubIngestionError(f"GitHub returned an error: HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        raise GithubIngestionError(f"Could not reach GitHub: {e}")

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise GithubIngestionError("That file doesn't look like text (binary file?).")

    if not text.strip():
        raise GithubIngestionError("That file is empty.")

    display_name = raw_url.rsplit("/", 1)[-1]

    CHARS_PER_PAGE = 3000
    pages = [
        {"page": i // CHARS_PER_PAGE + 1, "text": text[i : i + CHARS_PER_PAGE]}
        for i in range(0, len(text), CHARS_PER_PAGE)
    ]

    logger.info("Ingested GitHub file %s (%d chars, %d pages)", raw_url, len(text), len(pages))

    return pages, display_name
