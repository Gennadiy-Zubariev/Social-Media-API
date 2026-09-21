import re

HASHTAG_RE = re.compile(r"#(\w+)")


def parse_hashtags(content):
    return HASHTAG_RE.findall(content.lower())
