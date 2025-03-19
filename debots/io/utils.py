import re
ansi_pattern = re.compile(r'\033\[[0-9;]*m')

def remove_ansi_codes(text: str) -> str:
    return ansi_pattern.sub('', text)