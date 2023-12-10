import re

def contains_midnight_phrase(text: str) -> bool:
    # Use regexp for matching "hyv*ke[ks|sk]iyö*"?
    midnight_strings = ["happy midnight", "hyvää keskiyötä", "hyvää keksiyötä"]
    text_lower = text.lower()
    return any((s in text_lower for s in midnight_strings))



def message_to_trophy(msg:str) -> str:
    match = re.search('(h.*?i.*?n.*?t)|(h.*?k.*?t.*?ä)', msg, re.IGNORECASE)
    matchtext = match.group()
    if bool(re.search('keksi', matchtext, re.IGNORECASE)):
        return '🍪'
    return '🏆'
