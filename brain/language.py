import re

GUJARATI_WORDS = {
    "shu", "su", "kem", "chhe", "che", "tame", "tu", "maru", "mare", "mane",
    "kai", "kya", "kyare", "have", "pachi", "karvu", "karie", "joie", "nathi",
    "haan", "aaje", "apde", "mara", "tari", "tane", "thay", "thase", "sakay",
    "saku", "bol", "aapde", "aap", "mokal", "kari", "kare", "kar", "joi",
    "padse", "baddha", "badhha", "ghar", "kale",
}

HINDI_WORDS = {
    "kya", "hai", "haan", "nahi", "mujhe", "mera", "meri", "tum", "aap",
    "kaise", "karna", "batao", "abhi", "aaj", "mujhko", "kyun", "karo",
}

GUJARATI_CHAR = re.compile(r"[\u0A80-\u0AFF]")
HINDI_CHAR = re.compile(r"[\u0900-\u097F]")


def detect_language(text):
    if GUJARATI_CHAR.search(text):
        return "gu"
    if HINDI_CHAR.search(text):
        return "hi"
    words = re.findall(r"[a-z]+", text.lower())
    gujarati_hits = sum(1 for w in words if w in GUJARATI_WORDS)
    hindi_hits = sum(1 for w in words if w in HINDI_WORDS)
    if gujarati_hits >= 2 and gujarati_hits >= hindi_hits:
        return "gu"
    if hindi_hits >= 2:
        return "hi"
    return "en"