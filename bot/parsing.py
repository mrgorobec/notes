import re

URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://\S+$", re.IGNORECASE)


def parse_line(line: str) -> tuple[str, str]:
    """`логін: sasha` → ("логін", "sasha"); a bare URL → ("посилання", url); else a note."""
    if URL_RE.match(line):
        return "посилання", line
    idx = line.find(":")
    # "зустріч о 10:30" is a note, not key "зустріч о 10"
    is_time = 0 < idx < len(line) - 1 and line[idx - 1].isdigit() and line[idx + 1].isdigit()
    key, value = line[:idx].strip(), line[idx + 1 :].strip()
    if idx > 0 and key and value and len(key) <= 64 and not is_time:
        return key, value
    return "нотатка", line


def parse_fields(text: str) -> list[dict]:
    """One field per non-empty line."""
    fields = []
    for raw in text.splitlines():
        line = raw.strip()
        if line:
            key, value = parse_line(line)
            fields.append({"key": key, "value": value[:4000]})
    return fields
