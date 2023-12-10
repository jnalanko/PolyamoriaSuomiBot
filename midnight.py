import re

def contains_midnight_phrase(text: str) -> bool:
	match = re.search('(h.*?i.*?n.*?t)|(h.*?k.*?t.*?ä)', text, re.IGNORECASE)
	if not match or len(match.group()) > 20:
		return False
	n_edits = min(
		distance(match.group(), "happy midnight"),
		distance(match.group(), "hyvää keskiyötä")
		)
	return n_edits <= 3

def distance(t1:str, t2:str):
	return caching_levenshtein(t1.lower(), t2.lower())

def caching_levenshtein(t1:str, t2:str, cache:dict = {}):
	if len(t1) == 0:
		return len(t2)
	if len(t2) == 0:
		return len(t1)
	if (t1,t2) in cache:
		return cache[(t1,t2)]
	if (t1[0] == t2[0]):
		cache[(t1,t2)] = caching_levenshtein(t1[1:], t2[1:], cache)
		return cache[(t1,t2)]
	cache[(t1,t2)] = 1 + min(
		caching_levenshtein(t1[1:], t2,     cache),
		caching_levenshtein(t1,     t2[1:], cache),
		caching_levenshtein(t1[1:], t2[1:], cache)
		)
	return cache[(t1,t2)]
