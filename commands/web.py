from urllib.parse import quote_plus

from utils.platform import open_url

WEBSITES = {
    "open gmail": "https://mail.google.com",
    "open github": "https://github.com",
    "open chatgpt": "https://chatgpt.com",
    "open whatsapp web": "https://web.whatsapp.com",
    "open whatsapp": "https://web.whatsapp.com",
    "open youtube": "https://www.youtube.com",
    "open google": "https://www.google.com",
    "open twitter": "https://twitter.com",
    "open x": "https://x.com",
    "open facebook": "https://www.facebook.com",
    "open instagram": "https://www.instagram.com",
    "open linkedin": "https://www.linkedin.com",
    "open reddit": "https://www.reddit.com",
    "open netflix": "https://www.netflix.com",
    "open amazon": "https://www.amazon.com",
}


def handle(user_input):
    lower = user_input.lower().strip()

    for cmd, url in WEBSITES.items():
        if lower == cmd:
            open_url(url)
            return f"Opening {url.split('//')[1].split('/')[0]}, Prince."

    if lower.startswith("search google for "):
        query = user_input[len("search google for "):]
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        open_url(url)
        return f"Searching Google for '{query}', Prince."

    if lower.startswith("google search "):
        query = user_input[len("google search "):]
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        open_url(url)
        return f"Searching Google for '{query}', Prince."

    if lower.startswith("search youtube for "):
        query = user_input[len("search youtube for "):]
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        open_url(url)
        return f"Searching YouTube for '{query}', Prince."

    if lower.startswith("youtube search "):
        query = user_input[len("youtube search "):]
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        open_url(url)
        return f"Searching YouTube for '{query}', Prince."

    if lower.startswith("open "):
        target = lower[5:].strip().replace(" ", "")
        if len(target) > 2:
            url = f"https://www.{target}.com"
            open_url(url)
            return f"Opening {target}.com, Prince."

    return None
