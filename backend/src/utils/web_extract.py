"""
Website ingestion: fetch a URL, extract the readable article content
(stripping nav/ads/boilerplate), split into page-like chunks for citation
purposes, and hand back the same {page, text} shape utils/pdf.py produces
-- so it can go through the exact same chunk/embed/store pipeline as a PDF.

SECURITY: this fetches a URL on the server's behalf, at a logged-in
user's request. Without guardrails, that's a textbook SSRF vector --
someone could point it at http://169.254.169.254/ (cloud metadata),
http://localhost:PORT/internal-admin, or an internal-only service the
backend can reach but the public internet can't. _validate_public_url
blocks that class of request before any fetch happens.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse
import trafilatura

import httpx

from src.core.logging import logger

MAX_CONTENT_BYTES = 15 * 1024 * 1024  # 15MB cap on the raw page fetch
FETCH_TIMEOUT_SECONDS = 15
CHARS_PER_PAGE = 3000  # splits long articles into citation-friendly "pages"

# Wikimedia explicitly documents and supports this REST endpoint for
# programmatic use (https://en.wikipedia.org/api/rest_v1/), unlike scraping
# the rendered article page, which its edge blocks for generic/bot-looking
# User-Agents. Hitting the API instead of trafilatura-scraping the HTML
# avoids the 403 entirely and gives cleaner article text besides.
_WIKIPEDIA_HOST_RE = re.compile(r"^([a-z0-9-]+)\.wikipedia\.org$", re.IGNORECASE)

# A generic string containing "bot" gets 403'd by several sites' edges,
# Wikimedia included. Per https://meta.wikimedia.org/wiki/User-Agent_policy
# and general good-citizen practice, self-identifying honestly (app name +
# contact) is both more compliant and less likely to be blocked than
# pretending to be a browser or hiding behind an anonymous "bot" UA.
DEFAULT_USER_AGENT = (
    "AIKnowledgeWorkspace/1.0 "
    "(+https://github.com/your-org/ai-knowledge-workspace; contact@example.com) "
    "httpx"
)


class UrlIngestionError(Exception):
    pass


def _validate_public_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise UrlIngestionError("Only http:// and https:// URLs are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise UrlIngestionError("Could not determine the hostname from that URL.")

    if hostname.lower() in ("localhost", "0.0.0.0"):
        raise UrlIngestionError("That host isn't allowed.")

    # Resolve the hostname and reject anything that lands in a private,
    # loopback, link-local, or reserved range -- this is the actual SSRF
    # guard. Checking the hostname string alone isn't enough (DNS
    # rebinding, "127.0.0.1.nip.io", decimal/octal IP encodings, etc.).
    try:
        resolved_ips = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror:
        raise UrlIngestionError(f"Could not resolve host: {hostname}")

    for ip_str in resolved_ips:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            raise UrlIngestionError(
                "That URL resolves to a private/internal address, which isn't allowed."
            )

    return url


def _wikipedia_article_title(url: str) -> str | None:
    """If url is a *.wikipedia.org/wiki/<Title> article link, return the
    decoded title. Otherwise return None so callers fall back to the
    generic scraper (e.g. Wikipedia search/diff/history pages, non-article
    namespaces, etc. aren't handled by this fast path)."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if not _WIKIPEDIA_HOST_RE.match(hostname):
        return None

    parts = parsed.path.split("/", 2)
    # path looks like /wiki/World_War_II
    if len(parts) < 3 or parts[1] != "wiki" or not parts[2]:
        return None

    from urllib.parse import unquote

    title = unquote(parts[2])
    # Skip non-article namespaces (Talk:, Special:, File:, etc.)
    if ":" in title and title.split(":", 1)[0] in (
        "Talk", "Special", "File", "Category", "Template", "Help",
        "Wikipedia", "Portal", "Module", "User",
    ):
        return None
    return title


def _fetch_wikipedia_via_api(url: str, article_title: str) -> tuple[list[dict], str]:
    """Pull plain-text article content from Wikimedia's documented REST
    API instead of scraping the rendered page. This is the endpoint
    Wikimedia intends for programmatic access, so it doesn't hit the
    anti-scraping UA checks that block a generic HTML fetch."""
    parsed = urlparse(url)
    api_url = (
        f"https://{parsed.hostname}/w/api.php"
        f"?action=query&prop=extracts&explaintext=1&format=json"
        f"&titles={article_title}"
    )

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        ) as client:
            response = client.get(api_url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise UrlIngestionError(f"That URL returned an error: HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        raise UrlIngestionError(f"Could not reach that URL: {e}")
    except ValueError:
        raise UrlIngestionError("Wikipedia API returned an unexpected response.")

    pages_data = data.get("query", {}).get("pages", {})
    if not pages_data:
        raise UrlIngestionError("Could not find that Wikipedia article.")

    page = next(iter(pages_data.values()))
    if "missing" in page:
        raise UrlIngestionError(f"Wikipedia article '{article_title}' does not exist.")

    extracted = page.get("extract", "")
    title = page.get("title", article_title)

    if not extracted or len(extracted.strip()) < 50:
        raise UrlIngestionError(
            "Could not extract readable article content from that Wikipedia page."
        )

    pages = []
    for i in range(0, len(extracted), CHARS_PER_PAGE):
        pages.append({"page": len(pages) + 1, "text": extracted[i : i + CHARS_PER_PAGE]})

    logger.info(
        "Extracted %d chars (%d pages) from Wikipedia API for %s", len(extracted), len(pages), title
    )
    return pages, title


def fetch_and_extract_url(url: str) -> tuple[list[dict], str]:
    """Returns (pages, page_title) where pages matches utils/pdf.py's
    [{"page": N, "text": "..."}] shape."""

    validated_url = _validate_public_url(url)

    # Fast path: Wikipedia article pages go through Wikimedia's own REST
    # API rather than scraping the rendered HTML, which sidesteps the
    # anti-bot 403s the generic path runs into on wikipedia.org.
    article_title = _wikipedia_article_title(validated_url)
    if article_title:
        try:
            return _fetch_wikipedia_via_api(validated_url, article_title)
        except UrlIngestionError:
            # Fall through to the generic scraper below in case the API
            # path itself has an issue (e.g. odd title edge case) -- better
            # to attempt the normal route than fail outright.
            logger.warning("Wikipedia API fast path failed for %s, falling back to scraping", validated_url)

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        ) as client:
            # Stream so we can enforce the size cap without buffering an
            # arbitrarily large response into memory first.
            with client.stream("GET", validated_url) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    raise UrlIngestionError(
                        f"That URL returned '{content_type or 'unknown'}' content, not a web page."
                    )

                chunks = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_CONTENT_BYTES:
                        raise UrlIngestionError("That page is too large to ingest.")
                    chunks.append(chunk)
                html = b"".join(chunks)

            # IMPORTANT: re-validate on the URL actually reached after any
            # redirects, since the target of a redirect could point
            # somewhere the original URL didn't (a second SSRF vector).
            _validate_public_url(str(response.url))

    except httpx.HTTPStatusError as e:
        raise UrlIngestionError(f"That URL returned an error: HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        raise UrlIngestionError(f"Could not reach that URL: {e}")

    import trafilatura

    extracted = trafilatura.extract(
        html, include_comments=False, include_tables=True, favor_recall=True
    )
    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata else None) or validated_url

    if not extracted or len(extracted.strip()) < 50:
        raise UrlIngestionError(
            "Could not extract readable article content from that page "
            "(it may be mostly JavaScript-rendered, paywalled, or not article-shaped)."
        )

    # Split into fixed-size "pages" purely so citations have a page
    # number to point at -- a website has no real pages, this is just
    # for consistency with the PDF citation UI.
    pages = []
    for i in range(0, len(extracted), CHARS_PER_PAGE):
        pages.append({"page": len(pages) + 1, "text": extracted[i : i + CHARS_PER_PAGE]})

    logger.info("Extracted %d chars (%d pages) from %s", len(extracted), len(pages), validated_url)

    return pages, title