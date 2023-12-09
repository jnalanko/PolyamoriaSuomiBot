import re

def contains_midnight_phrase(text: str) -> bool:
    return bool(re.search('(h.*i.*n.*)|(h.*k.*t.*)', text, re.IGNORECASE))
