from commands import apps, system, media, files, web, settings, clipboard, timer

HANDLERS = [
    apps.handle,
    system.handle,
    media.handle,
    files.handle,
    web.handle,
    settings.handle,
    clipboard.handle,
    timer.handle,
]


def needs_web_search(text):
    keywords = [
        "latest", "today", "current", "news", "recent", "weather", "price",
        "stock", "online", "internet", "search web", "google", "find online",
        "aaje", "atyare", "bhav", "khabar", "aaj", "abhi", "samachar",
    ]
    lower = text.lower()
    return any(w in lower for w in keywords)


def route(user_input):
    for handler in HANDLERS:
        result = handler(user_input)
        if result is not None:
            return result, False
    return None, needs_web_search(user_input)
