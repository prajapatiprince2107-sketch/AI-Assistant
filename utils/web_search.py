import os
import re
from html import unescape
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

tavily = None
if TavilyClient and TAVILY_API_KEY:
    tavily = TavilyClient(api_key=TAVILY_API_KEY)


def web_search(query):
    if tavily is not None:
        try:
            response = tavily.search(
                query=query,
                search_depth="basic",
                max_results=5,
            )
            results = response.get("results", [])
            if results:
                context = ""
                for i, r in enumerate(results, 1):
                    context += (
                        f"\nRESULT {i}\n"
                        f"TITLE: {r.get('title', '')}\n"
                        f"URL: {r.get('url', '')}\n"
                        f"CONTENT: {r.get('content', '')}\n"
                    )
                return context
        except Exception:
            pass

    try:
        url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
        request = Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
        })
        with urlopen(request, timeout=8) as response:
            html_text = response.read().decode("utf-8", errors="ignore")

        blocks = re.findall(
            r'<div[^>]+class="result[^"]*"[\s\S]*?</div>\s*</div>',
            html_text,
            flags=re.IGNORECASE,
        )

        context = ""
        count = 0

        for block in blocks:
            title_match = re.search(
                r'class="result__a"[^>]*>(.*?)</a>',
                block,
                flags=re.IGNORECASE | re.DOTALL,
            )
            snippet_match = re.search(
                r'class="result__snippet"[^>]*>(.*?)</',
                block,
                flags=re.IGNORECASE | re.DOTALL,
            )
            url_match = re.search(
                r'class="result__url"[^>]*>(.*?)</a>',
                block,
                flags=re.IGNORECASE | re.DOTALL,
            )

            if not title_match:
                continue

            title = unescape(" ".join(
                re.sub(r"<[^>]+>", "", title_match.group(1)).split()
            ))
            snippet = ""
            if snippet_match:
                snippet = unescape(" ".join(
                    re.sub(r"<[^>]+>", "", snippet_match.group(1)).split()
                ))
            result_url = ""
            if url_match:
                result_url = unescape(" ".join(
                    re.sub(r"<[^>]+>", "", url_match.group(1)).split()
                ))

            count += 1
            context += (
                f"\nRESULT {count}\n"
                f"TITLE: {title}\n"
                f"URL: {result_url}\n"
                f"CONTENT: {snippet}\n"
            )

            if count >= 5:
                break

        return context

    except Exception:
        return ""
