def contains_midnight_phrase(text: str) -> bool:
    # Use regexp for matching "hyv*ke[ks|sk]iyö*"?
    midnight_strings = ["happy midnight", "hyvää keskiyötä", "hyvää keksiyötä"]
    text_lower = text.lower()
    return any((s in text_lower for s in midnight_strings))
