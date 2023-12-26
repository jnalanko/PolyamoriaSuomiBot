from datetime import date

def contains_midnight_phrase(text: str) -> bool:
    # Use regexp for matching "hyv*ke[ks|sk]iyö*"?
    midnight_strings = ["happy midnight", "hyvää keskiyötä", "hyvää keksiyötä"]
    text_lower = text.lower()
    return any((s in text_lower for s in midnight_strings))

# Assuming this message won on this date, what is the prize?
# The prize is always a single unicode character, i.e. a string of length 1.
def get_prize(text: str, date: date) -> str:
    if date.month == 1 and date.day == 1: # First day of the year
        return '👑'
    elif "keksiyö" in text:
        return '🍪'
    else:
        return '🏆'
    
# Returns an integer that should be used as a sort key when listing the trophy counts of a user
def trophy_sort_key(trophy: str) -> int:
    assert(len(trophy) == 1)
    if trophy == '🏆': return 0 
    elif trophy == '👑': return 1
    else: return ord(trophy) # The rank of the character in unicode

# Takes a list of counts like [('🏆', 4), ('🍪', 5), ('👑', 1)].
# Returns a string describing the counts.
def format_trophy_counts(counts: list) -> str:
    counts.sort(key = lambda X : trophy_sort_key(X[0]))
    return ", ".join([X[0] + " × " + str(X[1]) for X in counts])

