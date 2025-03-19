import re
from .ParsedPage import ParsedPage

pattern_with_url = re.compile(r'in (?:page|file) "(.*)":\n\((.*)\)\n((?:\d+\|.*\n?)+)')
pattern_without_url = re.compile(r'in (?:page|file) "(.*)":\n((?:\d+\|.*\n?)+)')

def parse_raw_lines(raw_lines: str) -> [(int, str)]:
    to_return = []
    for raw_line in filter(None, raw_lines.splitlines()):
        line_idx_str, line_content_str = raw_line.split("|", maxsplit=1)
        line_idx = int(line_idx_str)
        line_content_str = line_content_str.strip()
        to_return.append((line_idx, line_content_str))
    return to_return

def parse_with_url(content) -> [ParsedPage]:
    global pattern_with_url
    matches = re.findall(pattern_with_url, content)
    to_return = []
    for match in matches:
        title = match[0]
        url = match[1]
        raw_lines = match[2]
        lines = parse_raw_lines(raw_lines)
        to_return.append(ParsedPage(title, url, lines))
    return to_return

def parse_without_url(content) -> [ParsedPage]:
    global pattern_without_url
    matches = re.findall(pattern_without_url, content)
    to_return = []
    for match in matches:
        title = match[0]
        raw_lines = match[1]
        lines = parse_raw_lines(raw_lines)
        to_return.append(ParsedPage(title, "", lines))
    return to_return

def parse(content) -> [ParsedPage]:
    return parse_with_url(content) + parse_without_url(content)